#!/usr/bin/env python3
"""CLI verifier for the Windows offline data-pack bundle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_offline_data_pack_index import verify_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", type=Path, required=True)
    args = parser.parse_args()
    result = verify_bundle(args.pack_dir.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
