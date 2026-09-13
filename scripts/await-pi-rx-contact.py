#!/usr/bin/env python3

import argparse
import json
import struct
import time
from pathlib import Path


CONTACT_RECORD_SIZE = 152
PUB_KEY_SIZE = 32


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wait for the Pi donor runtime to persist a new or updated received contact advert."
    )
    parser.add_argument(
        "--storage-root",
        default="/var/lib/meshcore-pi-port",
        help="Pi storage root used by the live runtime",
    )
    parser.add_argument(
        "--contacts-path",
        type=Path,
        help="Override the contacts file path instead of deriving it from --storage-root",
    )
    parser.add_argument(
        "--expect-pub-key",
        help="Only succeed when the changed contact matches this 64-char hex public key",
    )
    parser.add_argument(
        "--expect-name",
        help="Only succeed when the changed contact name contains this case-insensitive substring",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="Seconds to wait for a persisted contact change",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds between file polls",
    )
    parser.add_argument(
        "--show-baseline",
        action="store_true",
        help="Print the initial contact snapshot before waiting",
    )
    return parser.parse_args()


def resolve_contacts_path(args: argparse.Namespace) -> Path:
    if args.contacts_path is not None:
        return args.contacts_path
    return Path(args.storage_root) / "channels" / "contacts3"


def load_contacts(path: Path) -> list[dict]:
    if not path.exists():
        return []

    data = path.read_bytes()
    contacts: list[dict] = []
    for offset in range(0, len(data), CONTACT_RECORD_SIZE):
        record = data[offset:offset + CONTACT_RECORD_SIZE]
        if len(record) < CONTACT_RECORD_SIZE:
            break
        pub_key = record[0:PUB_KEY_SIZE].hex()
        name = record[32:64].split(b"\0", 1)[0].decode("utf-8", "replace")
        contact = {
            "pub_key": pub_key,
            "name": name,
            "type": record[64],
            "flags": record[65],
            "sync_since": struct.unpack_from("<I", record, 67)[0],
            "out_path_len": record[71],
            "last_advert_timestamp": struct.unpack_from("<I", record, 72)[0],
            "lastmod": struct.unpack_from("<I", record, 140)[0],
            "gps_lat_e6": struct.unpack_from("<i", record, 144)[0],
            "gps_lon_e6": struct.unpack_from("<i", record, 148)[0],
        }
        contacts.append(contact)
    return contacts


def snapshot_by_pub_key(path: Path) -> dict[str, dict]:
    return {contact["pub_key"]: contact for contact in load_contacts(path)}


def contact_matches(contact: dict, args: argparse.Namespace) -> bool:
    if args.expect_pub_key is not None and contact["pub_key"] != args.expect_pub_key.lower():
        return False
    if args.expect_name is not None and args.expect_name.lower() not in contact["name"].lower():
        return False
    return True


def describe_change(previous: dict | None, current: dict) -> dict:
    if previous is None:
        return {
            "change": "new_contact",
            "contact": current,
        }

    changed_fields = []
    for field in (
        "name",
        "type",
        "flags",
        "sync_since",
        "out_path_len",
        "last_advert_timestamp",
        "lastmod",
        "gps_lat_e6",
        "gps_lon_e6",
    ):
        if previous.get(field) != current.get(field):
            changed_fields.append(field)

    return {
        "change": "updated_contact",
        "changed_fields": changed_fields,
        "previous": previous,
        "contact": current,
    }


def main() -> int:
    args = parse_args()
    contacts_path = resolve_contacts_path(args)
    baseline = snapshot_by_pub_key(contacts_path)

    if args.show_baseline:
        print(
            json.dumps(
                {
                    "contacts_path": str(contacts_path),
                    "baseline_count": len(baseline),
                    "baseline": list(baseline.values()),
                },
                indent=2,
                sort_keys=True,
            )
        )

    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        current = snapshot_by_pub_key(contacts_path)
        for pub_key, contact in current.items():
            previous = baseline.get(pub_key)
            if previous == contact:
                continue
            if not contact_matches(contact, args):
                continue
            print(
                json.dumps(
                    {
                        "contacts_path": str(contacts_path),
                        "detected_at": int(time.time()),
                        **describe_change(previous, contact),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        time.sleep(args.poll_interval)

    print(
        json.dumps(
            {
                "contacts_path": str(contacts_path),
                "timeout": args.timeout,
                "error": "timed out waiting for a new or updated contact record",
                "filters": {
                    "expect_pub_key": args.expect_pub_key.lower() if args.expect_pub_key else None,
                    "expect_name": args.expect_name,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())