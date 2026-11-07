#!/usr/bin/env python3
"""Read-only schema probe for ASTRA's public third-generation TARGA automobile file.

The probe reads only a bounded HTTP range, never imports rows, and never writes
source data into the product catalog. It records transport metadata and checks
the published fixed-column schema against a small TSV sample.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import unicodedata
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = (
    "https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/"
    "2200-Basisdaten_TG_ab_1995/TG-Automobil.txt"
)
DATA_DESCRIPTION_URL = (
    "https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/"
    "2200-Basisdaten_TG_ab_1995/2220-Datenbeschreibung/Basisdaten_TG_ab_1995.pdf"
)
ASTRA_OPEN_DATA_URL = "https://www.astra.admin.ch/de/news-homologation"
OGD_TERMS_URL = "https://opendata.swiss/en/terms-of-use"
OGD_FAQ_URL = "https://opendata.swiss/en/faq"
EMBAG_URL = "https://www.fedlex.admin.ch/eli/cc/2023/682/en"

# Zero-based positions from ASTRA's published TG-Basisdaten field list.
FIELDS = {
    "approval_number": 0,
    "approval_date": 1,
    "vehicle_group": 6,
    "vehicle_class": 9,
    "make": 10,
    "type": 11,
    "variant_version": 12,
    "eu_whole_vehicle_approval": 17,
    "gearbox_1": 26,
    "gearbox_1_final_drive_ratio": 27,
    "gearbox_1_assignment": 28,
    "gearbox_2": 29,
    "gearbox_2_final_drive_ratio": 30,
    "gearbox_2_assignment": 31,
    "engine_make": 59,
    "engine_type": 60,
    "engine_construction": 61,
    "fuel": 62,
    "displacement_cc": 63,
    "power_kw": 64,
    "power_rpm": 65,
    "max_torque_nm": 66,
    "max_torque_rpm": 67,
    "engine_marking": 75,
    "engine_marking_location": 76,
}
MIN_REQUIRED_COLUMNS = max(FIELDS.values()) + 1
VAG_MAKES = {
    "VW", "VOLKSWAGEN", "AUDI", "SEAT", "SKODA", "ŠKODA",
    "CUPRA", "PORSCHE", "BENTLEY", "LAMBORGHINI", "BUGATTI",
}
PREVIEW_LIMIT = 2 * 1024 * 1024


def normalize_make(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").strip().upper().split())


def decode_preview(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding, errors="strict"), encoding
        except UnicodeDecodeError:
            pass
    raise ValueError("Could not decode preview using supported Western encodings")


def parse_preview(raw: bytes) -> dict:
    text, encoding = decode_preview(raw)
    # A range can end in the middle of a record. Only parse complete physical
    # lines; quoted newlines are reported as a limitation, not silently repaired.
    last_newline = max(text.rfind("\n"), text.rfind("\r"))
    complete = text[:last_newline] if last_newline >= 0 else ""
    rows = list(csv.reader(io.StringIO(complete), delimiter="\t", quotechar='"'))
    rows = [row for row in rows if row and any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError("No complete TSV rows found in bounded preview")

    header_like = any(
        "typengenehmigungsnummer" in normalize_make(cell).lower()
        or "typengenehmigungsnummer" in cell.casefold()
        for cell in rows[0][:4]
    )
    header_fields = rows[0] if header_like else []
    header_field_count = len(header_fields)
    header_trailing_empty_fields = 0
    for value in reversed(header_fields):
        if value.strip():
            break
        header_trailing_empty_fields += 1
    if header_like:
        rows = rows[1:]

    lengths = [len(row) for row in rows]
    valid = [row for row in rows if len(row) >= MIN_REQUIRED_COLUMNS]
    make_counts: Counter[str] = Counter()
    first_vag = None
    for row in valid:
        make = row[FIELDS["make"]]
        normalized = normalize_make(make)
        if normalized in VAG_MAKES:
            make_counts[normalized] += 1
            if first_vag is None:
                first_vag = {
                    key: row[index].strip()
                    for key, index in FIELDS.items()
                    if key in {
                        "approval_number", "approval_date", "vehicle_class",
                        "make", "type", "variant_version",
                        "eu_whole_vehicle_approval", "gearbox_1",
                        "gearbox_1_final_drive_ratio", "gearbox_1_assignment",
                        "gearbox_2", "engine_make", "engine_type", "fuel",
                        "displacement_cc", "power_kw", "engine_marking",
                    }
                }

    return {
        "encoding": encoding,
        "complete_rows_in_preview": len(rows),
        "rows_meeting_published_field_schema": len(valid),
        "header_like_first_row": header_like,
        "header_field_count": header_field_count,
        "header_fields": header_fields,
        "header_trailing_empty_fields": header_trailing_empty_fields,
        "field_count_min": min(lengths) if lengths else None,
        "field_count_max": max(lengths) if lengths else None,
        "field_count_mode": Counter(lengths).most_common(1)[0][0] if lengths else None,
        "required_field_count": MIN_REQUIRED_COLUMNS,
        "vag_exact_make_counts_in_preview": dict(sorted(make_counts.items())),
        "first_vag_record_sample": first_vag,
        "published_field_positions": FIELDS,
        "vag_make_allowlist_exact_only": sorted(VAG_MAKES),
        "limitations": [
            "Bounded preview only; not a complete source snapshot.",
            "No source rows are imported by this probe.",
            "Approval-level engine markings and gearbox fields are not yet validated as VAG factory codes.",
            "The source is Switzerland-only and does not establish RU/EAEU applicability.",
            "No model year, generation, ECU, DTC or repair applicability is inferred.",
        ],
    }


def request_preview(url: str, limit: int = PREVIEW_LIMIT) -> tuple[bytes, dict]:
    request = urllib.request.Request(
        url,
        headers={
            "Range": f"bytes=0-{limit - 1}",
            "Accept-Encoding": "identity",
            "User-Agent": "VAG-TECH-PRO-source-schema-probe/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read(limit)
        headers = response.headers
        meta = {
            "http_status": response.status,
            "content_type": headers.get("Content-Type"),
            "content_length_header": headers.get("Content-Length"),
            "content_range": headers.get("Content-Range"),
            "accept_ranges": headers.get("Accept-Ranges"),
            "last_modified": headers.get("Last-Modified"),
            "etag": headers.get("ETag"),
            "range_requested_bytes": limit,
            "preview_bytes_read": len(raw),
            "range_response_confirmed": response.status == 206
            and (headers.get("Content-Range") or "").startswith("bytes 0-"),
        }
    return raw, meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="astra-targa-legacy-probe.json")
    args = parser.parse_args()
    report = {
        "schema_version": 1,
        "probe_kind": "bounded_read_only_schema_probe",
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_id_candidate": "astra-targa-legacy-third-generation",
        "publisher": "Federal Roads Office (FEDRO / ASTRA), Swiss Confederation",
        "market_scope": ["CH"],
        "source_url": SOURCE_URL,
        "data_description_url": DATA_DESCRIPTION_URL,
        "rights_evidence_urls": [
            ASTRA_OPEN_DATA_URL, OGD_TERMS_URL, OGD_FAQ_URL, EMBAG_URL
        ],
        "source_snapshot": {
            "downloaded": False,
            "full_file_sha256": None,
            "full_file_size_bytes": None,
            "hash_status": "No complete source file downloaded; full-source hash intentionally null.",
        },
    }
    try:
        raw, transport = request_preview(SOURCE_URL)
        parsed = parse_preview(raw)
        report["transport"] = transport
        report["preview_sha256"] = hashlib.sha256(raw).hexdigest()
        report["preview"] = parsed
        report["probe_status"] = (
            "schema_sample_valid"
            if parsed["rows_meeting_published_field_schema"] > 0
            else "schema_sample_inconclusive"
        )
    except Exception as exc:  # report network/parser failures as evidence
        report["probe_status"] = "probe_failed"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:1000]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "probe_status": report["probe_status"],
        "output": str(output),
        "error": report.get("error"),
        "transport": report.get("transport"),
        "preview": report.get("preview"),
    }, ensure_ascii=False, indent=2))
    return 0 if report["probe_status"] == "schema_sample_valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
