#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


CHANNEL_RECORD_SIZE = 68
MAX_NAME_BYTES = 32
SECRET_SIZE = 32


def load_channels(path: Path) -> list[dict]:
    if not path.exists():
        return []

    data = path.read_bytes()
    channels: list[dict] = []
    for offset in range(0, len(data), CHANNEL_RECORD_SIZE):
        record = data[offset:offset + CHANNEL_RECORD_SIZE]
        if len(record) < CHANNEL_RECORD_SIZE:
            break
        name = record[4:36].split(b"\0", 1)[0].decode("utf-8", "replace")
        secret = record[36:68].hex()
        channels.append(
            {
                "index": offset // CHANNEL_RECORD_SIZE,
                "name": name,
                "secret_hex": secret,
            }
        )
    return channels


def save_channels(path: Path, channels: list[dict]) -> None:
    data = bytearray()
    for channel in channels:
        record = bytearray(CHANNEL_RECORD_SIZE)
        name_bytes = channel["name"].encode("utf-8")[: MAX_NAME_BYTES - 1]
        record[4:36] = name_bytes + (b"\0" * (MAX_NAME_BYTES - len(name_bytes)))
        record[36:68] = bytes.fromhex(channel["secret_hex"])
        data.extend(record)
    path.write_bytes(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect or update MeshCore Pi persisted group channels")
    parser.add_argument("channels_path", type=Path)
    parser.add_argument("--index", type=int, help="Channel index to update")
    parser.add_argument("--name", help="New channel name")
    parser.add_argument("--secret-hex", help="New 64-character hex secret for the channel")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    channels = load_channels(args.channels_path)

    should_update = args.index is not None or args.name is not None or args.secret_hex is not None
    if not should_update:
        print(json.dumps(channels, indent=2, sort_keys=True))
        return 0

    if args.index is None:
        raise SystemExit("--index is required when updating channels")
    if args.index < 0:
        raise SystemExit("--index must be non-negative")

    while len(channels) <= args.index:
        channels.append(
            {
                "index": len(channels),
                "name": "",
                "secret_hex": "00" * SECRET_SIZE,
            }
        )

    channel = channels[args.index]
    if args.name is not None:
        channel["name"] = args.name
    if args.secret_hex is not None:
        secret_hex = args.secret_hex.lower()
        if len(secret_hex) != SECRET_SIZE * 2:
            raise SystemExit("--secret-hex must be exactly 64 hex characters")
        bytes.fromhex(secret_hex)
        channel["secret_hex"] = secret_hex

    save_channels(args.channels_path, channels)
    print(json.dumps(channels, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())