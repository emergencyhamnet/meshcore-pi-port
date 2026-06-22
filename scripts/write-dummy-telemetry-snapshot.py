#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a static Pi telemetry snapshot for app-mode alpha releases."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(os.environ.get("MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH", "/tmp/meshcore-pi-telemetry.env")),
    )
    parser.add_argument("--temperature-c", type=float, default=21.5)
    parser.add_argument("--humidity-pct", type=float, default=45.0)
    parser.add_argument("--pressure-hpa", type=float, default=1013.2)
    parser.add_argument("--vbat-v", type=float, default=4.10)
    parser.add_argument("--vin-v", type=float, default=5.00)
    parser.add_argument("--vout-v", type=float, default=5.00)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.path.parent.mkdir(parents=True, exist_ok=True)

    timestamp_unix = int(time.time())
    payload = "\n".join(
        [
            f"temperature_c={args.temperature_c:.2f}",
            f"humidity_pct={args.humidity_pct:.2f}",
            f"pressure_hpa={args.pressure_hpa:.2f}",
            f"vin_v={args.vin_v:.3f}",
            f"vout_v={args.vout_v:.3f}",
            f"vbat_v={args.vbat_v:.3f}",
            f"timestamp_unix={timestamp_unix}",
            "",
        ]
    )

    temp_path = args.path.with_suffix(args.path.suffix + ".tmp")
    temp_path.write_text(payload, encoding="utf-8")
    temp_path.replace(args.path)

    print(f"Wrote dummy telemetry snapshot to {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())