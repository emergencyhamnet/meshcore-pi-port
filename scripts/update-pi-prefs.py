#!/usr/bin/env python3
import argparse
import json
import struct
from pathlib import Path


PREFS_SIZE = 140


def load_prefs(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < PREFS_SIZE:
        raise ValueError(f"prefs file too short: {len(data)} bytes")

    prefs = {
        "airtime_factor": struct.unpack_from("<f", data, 0)[0],
        "node_name": data[4:36].split(b"\0", 1)[0].decode("utf-8", "replace"),
        "lat": struct.unpack_from("<d", data, 40)[0],
        "lon": struct.unpack_from("<d", data, 48)[0],
        "freq_mhz": struct.unpack_from("<f", data, 56)[0],
        "sf": data[60],
        "cr": data[61],
        "client_repeat": data[62],
        "manual_add_contacts": data[63],
        "bw_khz": struct.unpack_from("<f", data, 64)[0],
        "tx_power_dbm": struct.unpack_from("<b", data, 68)[0],
        "telemetry_mode_base": data[69],
        "telemetry_mode_loc": data[70],
        "telemetry_mode_env": data[71],
        "rx_delay_base": struct.unpack_from("<f", data, 72)[0],
        "advert_loc_policy": data[76],
        "multi_acks": data[77],
        "path_hash_mode": data[78],
        "ble_pin": struct.unpack_from("<I", data, 80)[0],
        "buzzer_quiet": data[84],
        "gps_enabled": data[85],
        "gps_interval_s": struct.unpack_from("<I", data, 86)[0],
        "autoadd_config": data[90],
        "autoadd_max_hops": data[91],
        "rx_boosted_gain": data[92],
        "default_scope_name": data[93:124].split(b"\0", 1)[0].decode("utf-8", "replace"),
        "default_scope_key_hex": data[124:140].hex(),
    }
    return prefs


def update_prefs(path: Path, args: argparse.Namespace) -> dict:
    data = bytearray(path.read_bytes())
    if len(data) < PREFS_SIZE:
        raise ValueError(f"prefs file too short: {len(data)} bytes")

    if args.node_name is not None:
        raw = args.node_name.encode("utf-8")[:31]
        data[4:36] = raw + (b"\0" * (32 - len(raw)))
    if args.lat is not None:
        struct.pack_into("<d", data, 40, args.lat)
    if args.lon is not None:
        struct.pack_into("<d", data, 48, args.lon)
    if args.freq_mhz is not None:
        struct.pack_into("<f", data, 56, args.freq_mhz)
    if args.sf is not None:
        data[60] = args.sf
    if args.cr is not None:
        data[61] = args.cr
    if args.client_repeat is not None:
        data[62] = args.client_repeat
    if args.manual_add_contacts is not None:
        data[63] = args.manual_add_contacts
    if args.bw_khz is not None:
        struct.pack_into("<f", data, 64, args.bw_khz)
    if args.tx_power_dbm is not None:
        struct.pack_into("<b", data, 68, args.tx_power_dbm)
    if args.advert_loc_policy is not None:
        data[76] = args.advert_loc_policy
    if args.multi_acks is not None:
        data[77] = args.multi_acks
    if args.path_hash_mode is not None:
        data[78] = args.path_hash_mode
    if args.ble_pin is not None:
        struct.pack_into("<I", data, 80, args.ble_pin)
    if args.gps_enabled is not None:
        data[85] = args.gps_enabled
    if args.gps_interval_s is not None:
        struct.pack_into("<I", data, 86, args.gps_interval_s)
    if args.autoadd_config is not None:
        data[90] = args.autoadd_config
    if args.autoadd_max_hops is not None:
        data[91] = args.autoadd_max_hops
    if args.rx_boosted_gain is not None:
        data[92] = args.rx_boosted_gain

    path.write_bytes(data)
    return load_prefs(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or update MeshCore Pi persisted donor prefs")
    parser.add_argument("prefs_path", type=Path)
    parser.add_argument("--node-name")
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lon", type=float)
    parser.add_argument("--freq-mhz", type=float)
    parser.add_argument("--bw-khz", type=float)
    parser.add_argument("--sf", type=int)
    parser.add_argument("--cr", type=int)
    parser.add_argument("--tx-power-dbm", type=int)
    parser.add_argument("--client-repeat", type=int)
    parser.add_argument("--manual-add-contacts", type=int)
    parser.add_argument("--advert-loc-policy", type=int)
    parser.add_argument("--multi-acks", type=int)
    parser.add_argument("--path-hash-mode", type=int)
    parser.add_argument("--ble-pin", type=int)
    parser.add_argument("--gps-enabled", type=int)
    parser.add_argument("--gps-interval-s", type=int)
    parser.add_argument("--autoadd-config", type=int)
    parser.add_argument("--autoadd-max-hops", type=int)
    parser.add_argument("--rx-boosted-gain", type=int)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.prefs_path.exists():
        parser.error(f"prefs file not found: {args.prefs_path}")

    editable_fields = [
        "node_name", "lat", "lon", "freq_mhz", "bw_khz", "sf", "cr", "tx_power_dbm",
        "client_repeat", "manual_add_contacts", "advert_loc_policy", "multi_acks",
        "path_hash_mode", "ble_pin", "gps_enabled", "gps_interval_s", "autoadd_config",
        "autoadd_max_hops", "rx_boosted_gain",
    ]
    should_update = any(getattr(args, field) is not None for field in editable_fields)

    prefs = update_prefs(args.prefs_path, args) if should_update else load_prefs(args.prefs_path)
    print(json.dumps(prefs, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())