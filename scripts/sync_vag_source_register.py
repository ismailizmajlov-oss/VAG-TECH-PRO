#!/usr/bin/env python3
"""Synchronize the authoritative source-rights register into the Windows desktop staging tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_and_validate(source_path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        source_stat = source_path.lstat()
    except OSError as exc:
        raise ValueError(f"Cannot stat source register: {exc}") from exc
    if not stat.S_ISREG(source_stat.st_mode) or source_path.is_symlink():
        raise ValueError("Source register must be a regular, non-symlink file")

    raw = source_path.read_bytes()
    try:
        manifest = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Source register is not valid UTF-8 JSON: {exc}") from exc

    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list):
        raise ValueError("Source register must be an object with a sources array")
    if not isinstance(manifest.get("updated_at"), str) or not manifest["updated_at"].strip():
        raise ValueError("Source register must have a non-empty updated_at value")

    seen: set[str] = set()
    for index, source in enumerate(manifest["sources"]):
        if not isinstance(source, dict):
            raise ValueError(f"Source entry {index} is not an object")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError(f"Source entry {index} has no source_id")
        if source_id in seen:
            raise ValueError(f"Duplicate source_id: {source_id}")
        seen.add(source_id)

        rights = source.get("rights") if isinstance(source.get("rights"), dict) else {}
        permission_status = str(rights.get("permission_status", "")).lower()
        verification_status = str(source.get("verification_status", "")).lower()
        restricted = permission_status in {"not_cleared", "not_obtained"} or "quarantined" in verification_status
        if restricted and source.get("data_ingested") is True:
            raise ValueError(f"Restricted/quarantined source cannot be marked ingested: {source_id}")

    if not seen:
        raise ValueError("Source register contains no source entries")
    return raw, manifest


def sync(source_path: str | Path, desktop_root: str | Path) -> dict[str, Any]:
    source = Path(source_path).absolute()
    root = Path(desktop_root).absolute()
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise ValueError("Desktop staging root must be an existing regular directory")

    raw, manifest = _read_and_validate(source)
    expected_hash = _sha256(raw)

    data_dir = root / "data"
    if data_dir.exists() and (data_dir.is_symlink() or not data_dir.is_dir()):
        raise ValueError("Desktop data path must be a regular directory")
    data_dir.mkdir(exist_ok=True)
    destination_dir = data_dir / "source-manifests"
    if destination_dir.exists() and (destination_dir.is_symlink() or not destination_dir.is_dir()):
        raise ValueError("Desktop source-manifests path must be a regular directory")
    destination_dir.mkdir(exist_ok=True)
    destination = destination_dir / "vag-factory-source-register.json"
    if destination.exists() and (destination.is_symlink() or not destination.is_file()):
        raise ValueError("Desktop source register destination must be a regular file")

    temp = destination.with_name(f".{destination.name}.{os.getpid()}.staging")
    try:
        with temp.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, destination)
        actual_hash = _sha256(destination.read_bytes())
        if actual_hash != expected_hash:
            raise ValueError("Desktop source register SHA-256 mismatch after atomic replacement")
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass

    return {
        "status": "synced_verified",
        "source": str(source),
        "destination": str(destination),
        "sha256": expected_hash,
        "source_count": len(manifest["sources"]),
        "updated_at": manifest["updated_at"],
        "data_ingested_count": sum(1 for item in manifest["sources"] if item.get("data_ingested") is True),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--desktop-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = sync(args.source, args.desktop_root)
    except Exception as exc:  # CLI must fail closed and provide a concise reason to CI.
        print(f"source-register-sync-error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
