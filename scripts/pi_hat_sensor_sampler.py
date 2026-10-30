#!/usr/bin/env python3

from __future__ import annotations

import argparse
import errno
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import signal
import tempfile
import threading
import time


def crc8(data: bytes) -> int:
    crc = 0xFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def signed_value(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def read_register(bus, address: int, register: int, length: int) -> bytes:
    from smbus2 import i2c_msg

    response = i2c_msg.read(address, length)
    bus.i2c_rdwr(i2c_msg.write(address, [register]), response)
    return bytes(response)


def write_register(bus, address: int, register: int, data: bytes) -> None:
    from smbus2 import i2c_msg

    bus.i2c_rdwr(i2c_msg.write(address, bytes([register]) + data))


def read_sht40(bus) -> dict[str, float]:
    from smbus2 import i2c_msg

    bus.i2c_rdwr(i2c_msg.write(0x44, [0xFD]))
    deadline = time.monotonic() + 0.15
    while True:
        response = i2c_msg.read(0x44, 6)
        try:
            bus.i2c_rdwr(response)
            data = bytes(response)
            break
        except OSError as error:
            if error.errno not in (errno.ENXIO, getattr(errno, 'EREMOTEIO', 121), errno.EIO) or time.monotonic() >= deadline:
                raise
    if crc8(data[:2]) != data[2] or crc8(data[3:5]) != data[5]:
        raise ValueError('SHT40 CRC mismatch')
    return {
        'temperature_c': -45 + 175 * int.from_bytes(data[:2], 'big') / 65535,
        'humidity_pct': max(0, min(100, -6 + 125 * int.from_bytes(data[3:5], 'big') / 65535)),
    }


def read_lps22hh(bus) -> dict[str, float]:
    if read_register(bus, 0x5C, 0x0F, 1)[0] != 0xB3:
        raise ValueError('Unexpected LPS22HH device identity')
    control1 = read_register(bus, 0x5C, 0x10, 1)[0]
    control2 = read_register(bus, 0x5C, 0x11, 1)[0]
    if control2 & 0x85:
        raise RuntimeError('LPS22HH busy or resetting')
    try:
        write_register(bus, 0x5C, 0x10, bytes([(control1 & 0x8F) | 0x02]))
        write_register(bus, 0x5C, 0x11, bytes([control2 | 0x11]))
        deadline = time.monotonic() + 0.5
        while read_register(bus, 0x5C, 0x11, 1)[0] & 1:
            if time.monotonic() >= deadline:
                raise TimeoutError('LPS22HH conversion timed out')
        while read_register(bus, 0x5C, 0x27, 1)[0] & 3 != 3:
            if time.monotonic() >= deadline:
                raise TimeoutError('LPS22HH data not ready')
        data = read_register(bus, 0x5C, 0x28, 5)
    finally:
        write_register(bus, 0x5C, 0x11, bytes([control2]))
        write_register(bus, 0x5C, 0x10, bytes([control1]))
    if (read_register(bus, 0x5C, 0x10, 1)[0], read_register(bus, 0x5C, 0x11, 1)[0]) != (control1, control2):
        raise RuntimeError('LPS22HH configuration restoration failed')
    return {
        'pressure_hpa': int.from_bytes(data[:3], 'little') / 4096,
        'pressure_temperature_c': signed_value(int.from_bytes(data[3:], 'little'), 16) / 100,
    }


def adc_voltage(register: bytes) -> float:
    return signed_value(int.from_bytes(register, 'big'), 16) / 16 * 0.002


def read_ads1015(bus, scales: dict[str, float]) -> dict[str, float]:
    original = int.from_bytes(read_register(bus, 0x48, 1, 2), 'big')
    readings = {}
    try:
        for channel, name in enumerate(('vin_v', 'vout_v', 'aux_v', 'vbat_v')):
            config = 0x8000 | ((4 + channel) << 12) | 0x0200 | 0x0100 | 0x0080 | 3
            write_register(bus, 0x48, 1, config.to_bytes(2, 'big'))
            deadline = time.monotonic() + 0.15
            while not int.from_bytes(read_register(bus, 0x48, 1, 2), 'big') & 0x8000:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'ADS1015 channel {channel} timed out')
            raw = read_register(bus, 0x48, 0, 2)
            if int.from_bytes(raw, 'big') & 0xF:
                raise ValueError('ADC output is not ADS1015 12-bit format')
            voltage = adc_voltage(raw)
            if abs(voltage) >= 4.08:
                raise ValueError(f'ADS1015 channel {channel} is saturated')
            readings[name] = voltage * scales[name]
    finally:
        write_register(bus, 0x48, 1, (original & 0x7FFF).to_bytes(2, 'big'))
    restored = int.from_bytes(read_register(bus, 0x48, 1, 2), 'big')
    if restored & 0x7FFF != original & 0x7FFF:
        raise RuntimeError('ADS1015 configuration restoration failed')
    return readings


def collect_snapshot(bus, *, scales: dict[str, float], sampled_at: datetime | None = None) -> dict:
    measurements: dict[str, float] = {}
    for label, reader in (('read_sht40', read_sht40), ('read_lps22hh', read_lps22hh)):
        try:
            measurements.update(reader(bus))
        except Exception as error:
            print(f'{label}: {error}', file=__import__('sys').stderr)
    try:
        measurements.update(read_ads1015(bus, scales))
    except Exception as error:
        print(f'read_ads1015: {error}', file=__import__('sys').stderr)
    timestamp = sampled_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError('Sample timestamp must include a timezone')
    return {'timestamp_unix': int(timestamp.timestamp()), 'measurements': measurements}


def write_snapshot(path: Path, snapshot: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'timestamp_unix={int(snapshot["timestamp_unix"])}']
    for key in ('temperature_c', 'humidity_pct', 'pressure_hpa', 'vbat_v'):
        value = snapshot.get('measurements', {}).get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            continue
        lines.append(f'{key}={value:.4f}')
    descriptor, temporary = tempfile.mkstemp(prefix='.meshcore-pi-telemetry-', dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write('\n'.join(lines) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description='Optional Pi HAT sensor sampler for native MeshCore telemetry.')
    parser.add_argument('--path', type=Path, default=Path('/tmp/meshcore-pi-telemetry.env'))
    parser.add_argument('--interval', type=float, default=10)
    parser.add_argument('--bus', type=int, default=1)
    parser.add_argument('--vin-scale', type=float, default=2)
    parser.add_argument('--vout-scale', type=float, default=2)
    parser.add_argument('--aux-scale', type=float, default=2)
    parser.add_argument('--vbat-scale', type=float, default=3.5)
    args = parser.parse_args()
    scales = {
        'vin_v': args.vin_scale, 'vout_v': args.vout_scale,
        'aux_v': args.aux_scale, 'vbat_v': args.vbat_scale,
    }
    if not math.isfinite(args.interval) or not 1 <= args.interval <= 3600:
        parser.error('Interval must be between 1 and 3600 seconds')
    if any(not math.isfinite(scale) or scale <= 0 for scale in scales.values()):
        parser.error('Voltage scale factors must be finite and positive')

    import fcntl
    from smbus2 import SMBus

    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    os.umask(0o077)
    lock_path = args.path.with_suffix(args.path.suffix + '.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        while not stopped.is_set():
            started = time.monotonic()
            try:
                with SMBus(args.bus) as bus:
                    snapshot = collect_snapshot(bus, scales=scales)
                write_snapshot(args.path, snapshot)
            except Exception as error:
                print(f'sensor sample failed: {error}', file=__import__('sys').stderr)
            stopped.wait(max(0, args.interval - (time.monotonic() - started)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())