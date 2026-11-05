#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rdw_vag_type_approval_common import verify_pack

def main() -> int:
    parser = argparse.ArgumentParser(description="Verify RDW VAG type-approval candidate pack")
    parser.add_argument("--pack-dir", required=True)
    parser.add_argument("--lock-path", default="data/source-manifests/rdw-vag-type-approval.lock.json")
    args = parser.parse_args()
    result = verify_pack(Path(args.pack_dir), Path(args.lock_path))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
