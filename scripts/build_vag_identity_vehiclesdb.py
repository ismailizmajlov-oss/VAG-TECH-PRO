#!/usr/bin/env python3
"""Build the isolated VehiclesDB VAG identity-candidate SQLite pack."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vag_identity_vehiclesdb_common import main_build

if __name__ == "__main__":
    raise SystemExit(main_build())
