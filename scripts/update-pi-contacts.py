#!/usr/bin/env python3
import argparse
import json
import struct
import time
from pathlib import Path


CONTACT_RECORD_SIZE = 152
PUB_KEY_SIZE = 32
MAX_PATH_SIZE = 64
OUT_PATH_UNKNOWN = 0xFF
ADV_TYPE_CHAT = 1


def decode_contact(record: bytes) -> dict:
    pub_key = record[0:32].hex()
    name = record[32:64].split(b"\0", 1)[0].decode("utf-8", "replace")
    contact_type = record[64]
    flags = record[65]
    sync_since = struct.unpack_from("<I", record, 67)[0]
    out_path_len = record[71]
    last_advert_timestamp = struct.unpack_from("<I", record, 72)[0]
    out_path = record[76:140]
    lastmod = struct.unpack_from("<I", record, 140)[0]
    gps_lat = struct.unpack_from("<i", record, 144)[0]
    gps_lon = struct.unpack_from("<i", record, 148)[0]
    return {
        "pub_key": pub_key,
        "name": name,
        "type": contact_type,
        "flags": flags,
        "sync_since": sync_since,
        "out_path_len": out_path_len,
        "out_path_hex": out_path[: max(0, min(out_path_len, MAX_PATH_SIZE))].hex() if out_path_len != OUT_PATH_UNKNOWN else "",
        "last_advert_timestamp": last_advert_timestamp,
        "lastmod": lastmod,
        "gps_lat_e6": gps_lat,
        "gps_lon_e6": gps_lon,
    }


def load_contacts(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = path.read_bytes()
    contacts = []
    for offset in range(0, len(data), CONTACT_RECORD_SIZE):
        record = data[offset:offset + CONTACT_RECORD_SIZE]
        if len(record) < CONTACT_RECORD_SIZE:
            break
        contacts.append(decode_contact(record))
    return contacts


def encode_contact(contact: dict) -> bytes:
    record = bytearray(CONTACT_RECORD_SIZE)
    pub_key = bytes.fromhex(contact["pub_key"])
    if len(pub_key) != PUB_KEY_SIZE:
        raise ValueError("pub_key must be 32 bytes / 64 hex chars")
    record[0:32] = pub_key

    name_raw = contact["name"].encode("utf-8")[:31]
    record[32:64] = name_raw + (b"\0" * (32 - len(name_raw)))
    record[64] = contact["type"]
    record[65] = contact["flags"]
    record[66] = 0
    struct.pack_into("<I", record, 67, contact["sync_since"])
    record[71] = contact["out_path_len"]
    struct.pack_into("<I", record, 72, contact["last_advert_timestamp"])

    out_path = bytes.fromhex(contact["out_path_hex"]) if contact["out_path_hex"] else b""
    record[76:140] = out_path[:MAX_PATH_SIZE] + (b"\0" * (MAX_PATH_SIZE - min(len(out_path), MAX_PATH_SIZE)))
    struct.pack_into("<I", record, 140, contact["lastmod"])
    struct.pack_into("<i", record, 144, contact["gps_lat_e6"])
    struct.pack_into("<i", record, 148, contact["gps_lon_e6"])
    return bytes(record)


def save_contacts(path: Path, contacts: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(encode_contact(contact) for contact in contacts)
    path.write_bytes(payload)


def add_or_update_contact(path: Path, args: argparse.Namespace) -> list[dict]:
    contacts = load_contacts(path)
    now = int(time.time())
    name = args.name or args.pub_key[:12]
    replacement = {
        "pub_key": args.pub_key.lower(),
        "name": name,
        "type": args.contact_type,
        "flags": args.flags,
        "sync_since": args.sync_since,
        "out_path_len": OUT_PATH_UNKNOWN,
        "out_path_hex": "",
        "last_advert_timestamp": args.last_advert_timestamp,
        "lastmod": args.lastmod if args.lastmod is not None else now,
        "gps_lat_e6": args.gps_lat_e6,
        "gps_lon_e6": args.gps_lon_e6,
    }

    updated = False
    for index, contact in enumerate(contacts):
        if contact["pub_key"] == replacement["pub_key"]:
            contacts[index] = replacement
            updated = True
            break

    if not updated:
        contacts.append(replacement)

    save_contacts(path, contacts)
    return contacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or update MeshCore Pi persisted contacts")
    parser.add_argument("contacts_path", type=Path)
    parser.add_argument("--add-pub-key")
    parser.add_argument("--name")
    parser.add_argument("--type", dest="contact_type", type=int, default=ADV_TYPE_CHAT)
    parser.add_argument("--flags", type=int, default=0)
    parser.add_argument("--sync-since", type=int, default=0)
    parser.add_argument("--last-advert-timestamp", type=int, default=0)
    parser.add_argument("--lastmod", type=int)
    parser.add_argument("--gps-lat-e6", type=int, default=0)
    parser.add_argument("--gps-lon-e6", type=int, default=0)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.add_pub_key is not None:
        args.pub_key = args.add_pub_key
        contacts = add_or_update_contact(args.contacts_path, args)
    else:
        contacts = load_contacts(args.contacts_path)
    print(json.dumps(contacts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())