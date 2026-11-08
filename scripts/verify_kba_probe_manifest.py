#!/usr/bin/env python3
"""Fail-closed check that a fresh KBA probe matches the pinned source manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

SOURCE_ID = "kba-de-whole-vehicle-type-approvals"
OFFICIAL = {"www.kba.de", "kba.de"}


def canonical_http_datetime(value: str | None) -> str | None:
    """Normalize HTTP-date and ISO-8601 timestamps to the same UTC representation."""
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def verify(probe_path: Path, manifest_path: Path) -> dict:
    raw_probe = probe_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    snapshot = manifest.get("snapshot", {})
    if hashlib.sha256(raw_probe).hexdigest() != snapshot.get("probe_report_sha256"):
        raise ValueError("Pinned KBA probe-report SHA-256 mismatch")

    probe = json.loads(raw_probe.decode("utf-8-sig"))
    if probe.get("source_id") != SOURCE_ID or manifest.get("source_id") != SOURCE_ID:
        raise ValueError("KBA source identity mismatch")
    if probe.get("status") != "resource_acquired_schema_available" or probe.get("probe_only") is not True:
        raise ValueError("KBA probe did not acquire a schema-verified source")
    if snapshot.get("probe_run_id") != 42481409966 or snapshot.get("probe_artifact_id") != 13618031218:
        raise ValueError("Pinned KBA probe run/artifact identity mismatch")
    if probe.get("product_import_allowed") is not False or probe.get("data_ingested") is not False:
        raise ValueError("KBA probe must remain outside product data")

    resource = probe.get("resource", {})
    url = urlparse(resource.get("final_url") or resource.get("url") or "")
    if resource.get("status") != 200 or url.scheme != "https" or url.hostname not in OFFICIAL:
        raise ValueError("KBA resource did not return HTTP 200 from the official HTTPS host")

    for probe_key, manifest_key in (("sha256", "file_sha256"), ("bytes", "byte_size"), ("etag", "etag")):
        if resource.get(probe_key) != snapshot.get(manifest_key):
            raise ValueError("Fresh KBA probe differs from pinned manifest: " + probe_key)

    probe_modified = canonical_http_datetime(resource.get("last_modified"))
    manifest_modified = canonical_http_datetime(snapshot.get("last_modified"))
    if not probe_modified or probe_modified != manifest_modified:
        raise ValueError("Fresh KBA probe differs from pinned manifest: last_modified")

    if snapshot.get("file_sha256") != snapshot.get("source_snapshot_sha256"):
        raise ValueError("KBA snapshot SHA-256 mismatch")
    if manifest.get("source_snapshot_sha256") != snapshot.get("source_snapshot_sha256"):
        raise ValueError("KBA manifest/source snapshot SHA-256 mismatch")
    if snapshot.get("status") != "resource_acquired_schema_available" or snapshot.get("downloaded") is not True:
        raise ValueError("KBA manifest snapshot is not acquired")
    if probe.get("market_scope") != ["DE"] or manifest.get("market_scope") != ["DE"]:
        raise ValueError("KBA market scope must remain DE-only")

    rights = manifest.get("rights", {})
    if rights.get("rights_status") != "approved_by_published_DL_DE_BY_2_0":
        raise ValueError("KBA licence status mismatch")
    for key in (
        "commercial_use_allowed",
        "display_allowed",
        "offline_cache_allowed",
        "bulk_reuse_allowed",
        "redistribution_allowed",
        "attribution_required",
    ):
        if rights.get(key) is not True:
            raise ValueError("KBA rights condition missing: " + key)

    schema = probe.get("workbook_schema") or {}
    sheets = schema.get("sheets") or []
    if schema.get("sheet_count") != 1 or len(sheets) != 1:
        raise ValueError("KBA worksheet count changed")
    sheet = sheets[0]
    header = [None if value == "" else value for value in sheet.get("header", [])]
    if (
        sheet.get("name") != snapshot.get("sheet_name")
        or sheet.get("header_row_number") != snapshot.get("header_row_number")
        or header != snapshot.get("header")
    ):
        raise ValueError("KBA worksheet header differs from pinned schema")
    if snapshot.get("source_row_count") != 3782 or snapshot.get("vag_related_label_candidate_count") != 918:
        raise ValueError("KBA reviewed row counts missing or changed")

    return {
        "status": "probe_matches_pinned_manifest",
        "source_id": SOURCE_ID,
        "source_snapshot_sha256": snapshot["source_snapshot_sha256"],
        "source_revision": snapshot["source_revision"],
        "source_bytes": snapshot["byte_size"],
        "source_rows": snapshot["source_row_count"],
        "vag_related_label_candidates": snapshot["vag_related_label_candidate_count"],
        "market_scope": "DE",
        "product_import_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.probe, args.source_manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
