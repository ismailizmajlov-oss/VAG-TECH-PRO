#!/usr/bin/env python3
"""Synchronize the authoritative source-rights register into the Windows desktop staging tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
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

        if not isinstance(source.get("data_ingested"), bool):
            raise ValueError(f"Source entry must declare a boolean data_ingested: {source_id}")

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
    source_dir = source.parent
    try:
        source_dir_stat = source_dir.lstat()
    except OSError as exc:
        raise ValueError(f"Cannot stat source-manifest directory: {exc}") from exc
    if not stat.S_ISDIR(source_dir_stat.st_mode) or source_dir.is_symlink():
        raise ValueError("Source-manifest directory must be a regular, non-symlink directory")
    canonical_name = "vag-factory-source-register.json"
    file_map: dict[str, tuple[bytes, dict[str, Any]]] = {canonical_name: (raw, manifest)}
    skipped_empty_files: list[str] = []
    for entry in sorted(source_dir.iterdir(), key=lambda item: item.name.casefold()):
        if entry.is_symlink():
            raise ValueError(f"Source-manifest directory contains a symlink: {entry.name}")
        if entry.resolve() == source.resolve():
            continue
        if entry.is_dir():
            continue
        if entry.name == "source-manifest-index.json":
            continue
        if entry.suffix.lower() != ".json":
            continue
        if entry.name == canonical_name:
            raise ValueError("A second source-register file would shadow the canonical register")
        try:
            entry_stat = entry.lstat()
            if not stat.S_ISREG(entry_stat.st_mode):
                raise ValueError(f"Source manifest is not a regular file: {entry.name}")
            if entry_stat.st_size == 0:
                skipped_empty_files.append(entry.name)
                continue
            entry_raw = entry.read_bytes()
            entry_json = json.loads(entry_raw.decode("utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot validate source manifest {entry.name}: {exc}") from exc
        if not isinstance(entry_json, dict):
            raise ValueError(f"Source manifest must be a JSON object: {entry.name}")
        file_map[entry.name] = (entry_raw, entry_json)
    manifest_files: list[dict[str, Any]] = []
    for name, (file_raw, file_json) in sorted(file_map.items()):
        item: dict[str, Any] = {"name": name, "sha256": _sha256(file_raw), "bytes": len(file_raw)}
        if isinstance(file_json.get("sources"), list):
            item["source_count"] = len(file_json["sources"])
        manifest_files.append(item)
    russian_entry = next((item for item in manifest_files if item["name"] == "russian-eaeu-otts-sources.json"), None)
    index = {"schema_version":1,"updated_at":manifest["updated_at"],"source_register_name":canonical_name,
             "source_register_sha256":expected_hash,"manifest_count":len(manifest_files),"files":manifest_files,"skipped_files":[{"name":name,"reason":"empty_file"} for name in sorted(skipped_empty_files)]}
    index_raw = (json.dumps(index,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
    index_hash = _sha256(index_raw)
    data_dir = root / "data"
    if data_dir.exists() and (data_dir.is_symlink() or not data_dir.is_dir()):
        raise ValueError("Desktop data path must be a regular directory")
    data_dir.mkdir(exist_ok=True)
    destination_dir = data_dir / "source-manifests"
    if destination_dir.exists() and (destination_dir.is_symlink() or not destination_dir.is_dir()):
        raise ValueError("Desktop source-manifests path must be a regular directory")
    staging_dir = Path(tempfile.mkdtemp(prefix=".source-manifests.",suffix=".staging",dir=str(data_dir)))
    backup_dir = data_dir / f".source-manifests.{uuid.uuid4().hex}.backup"
    destination = destination_dir / canonical_name
    swapped = False
    try:
        def copy_preserved_tree(source_tree: Path,target_tree: Path) -> None:
            target_tree.mkdir(exist_ok=True)
            for entry in source_tree.iterdir():
                if entry.is_symlink():
                    raise ValueError(f"Existing desktop source-manifests contains a symlink: {entry}")
                target = target_tree / entry.name
                if entry.is_dir():
                    copy_preserved_tree(entry,target)
                elif entry.is_file():
                    if source_tree == destination_dir and entry.suffix.lower()==".json":
                        continue
                    shutil.copy2(entry,target)
                else:
                    raise ValueError(f"Existing desktop source-manifests contains a special file: {entry}")
        if destination_dir.exists():
            copy_preserved_tree(destination_dir,staging_dir)
        for name,(file_raw,_) in file_map.items():
            target=staging_dir/name
            with target.open("xb") as handle:
                handle.write(file_raw); handle.flush(); os.fsync(handle.fileno())
        index_path=staging_dir/"source-manifest-index.json"
        with index_path.open("xb") as handle:
            handle.write(index_raw); handle.flush(); os.fsync(handle.fileno())
        for item in manifest_files:
            target=staging_dir/item["name"]
            if not target.is_file() or target.stat().st_size!=item["bytes"] or _sha256(target.read_bytes())!=item["sha256"]:
                raise ValueError(f"Source-manifest staging verification failed: {item['name']}")
        if _sha256(index_path.read_bytes())!=index_hash:
            raise ValueError("Source-manifest index SHA-256 mismatch before directory swap")
        if destination_dir.exists():
            os.replace(destination_dir,backup_dir)
        try:
            os.replace(staging_dir,destination_dir); swapped=True
        except Exception:
            if backup_dir.exists() and not destination_dir.exists(): os.replace(backup_dir,destination_dir)
            raise
        if backup_dir.exists(): shutil.rmtree(backup_dir)
    finally:
        if staging_dir.exists(): shutil.rmtree(staging_dir,ignore_errors=True)
        if backup_dir.exists() and not swapped and not destination_dir.exists(): os.replace(backup_dir,destination_dir)
    if _sha256(destination.read_bytes())!=expected_hash:
        raise ValueError("Desktop source register SHA-256 mismatch after atomic directory replacement")
    actual_index_hash=_sha256((destination_dir/"source-manifest-index.json").read_bytes())
    if actual_index_hash!=index_hash:
        raise ValueError("Desktop source-manifest index SHA-256 mismatch after atomic directory replacement")
    return {"status":"synced_verified","source":str(source),"destination":str(destination),"sha256":expected_hash,
            "source_count":len(manifest["sources"]),"updated_at":manifest["updated_at"],
            "data_ingested_count":sum(1 for item in manifest["sources"] if item.get("data_ingested") is True),
            "manifest_count":len(manifest_files),"manifest_files":manifest_files,"skipped_empty_files":sorted(skipped_empty_files),"manifest_index_sha256":actual_index_hash,
            "russian_eaeu_otts_manifest_sha256":russian_entry["sha256"] if russian_entry else None,
            "russian_eaeu_otts_source_count":russian_entry.get("source_count") if russian_entry else None}

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
