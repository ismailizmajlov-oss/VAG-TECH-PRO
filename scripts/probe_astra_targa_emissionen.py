#!/usr/bin/env python3
"""Bounded, read-only schema probe for ASTRA TARGA emissionen.txt."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import unicodedata
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = (
    "https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/"
    "2200-Basisdaten_TG_ab_1995/emissionen.txt"
)
DATA_DESCRIPTION_URL = (
    "https://www.astra.admin.ch/dam/de/sd-web/7fPLSFMqD6JR/informationsprodukte_typengenehmigungsdaten.pdf"
)
ASTRA_OPEN_DATA_URL = "https://www.astra.admin.ch/de/news-homologation"
ASTRA_VEHICLE_DATA_URL = "https://www.astra.admin.ch/de/fahrzeugdaten"
OGD_POLICY_URL = "https://www.bk.admin.ch/en/open-government-data-ogd-2"
PREVIEW_LIMIT = 2 * 1024 * 1024
REQUIRED_HEADERS = {
    "approval_number": ("tgcode", "typengenehmigungsnummer"),
    "make": ("marke",),
    "type_variant_version": ("typ",),
    "gearbox_classification": ("getriebe",),
    "final_drive_ratio": ("iachse",),
    "engine_make": ("motormarke",),
    "engine_type": ("motortyp",),
    "engine_construction": ("bauart",),
    "fuel": ("treibstoff",),
    "displacement_cc": ("hubraum",),
    "power_kw": ("leistung",),
    "torque_nm": ("drehmoment",),
    "emission_control": ("abgasreinigung",),
    "drive": ("antrieb",),
    "homologation_date": ("homologationsdatum",),
}
VAG_MAKES = {
    "VW", "VOLKSWAGEN", "AUDI", "SEAT", "SKODA", "ŠKODA",
    "CUPRA", "PORSCHE", "BENTLEY", "LAMBORGHINI", "BUGATTI",
}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return "".join(ch for ch in value if ch.isalnum())


def normalize_make(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").strip().upper().split())


def decode(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding, errors="strict"), encoding
        except UnicodeDecodeError:
            pass
    raise ValueError("Unsupported preview encoding")


def resolve_header_positions(header: list[str]) -> dict[str, int]:
    if len(header) < 42:
        raise ValueError(f"Expected at least 42 documented emissionen columns, got {len(header)}")
    normalized = [norm(value) for value in header]
    positions = {}
    for key, aliases in REQUIRED_HEADERS.items():
        matches = [index for index, value in enumerate(normalized) if value in aliases]
        if not matches:
            raise ValueError(f"Required ASTRA emissionen field {key!r} not found in header: {header}")
        positions[key] = matches[0]
    return positions


def parse_preview(raw: bytes) -> dict:
    text, encoding = decode(raw)
    last_newline = max(text.rfind("\n"), text.rfind("\r"))
    complete = text[:last_newline] if last_newline >= 0 else ""
    rows = list(csv.reader(io.StringIO(complete), delimiter="\t", quotechar='"'))
    rows = [row for row in rows if row and any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError("No complete emissionen TSV rows found")
    header = rows[0]
    positions = resolve_header_positions(header)
    data_rows = rows[1:]
    make_counts = Counter()
    first_vag = None
    invalid = 0
    for row in data_rows:
        if len(row) != len(header):
            invalid += 1
            continue
        make = normalize_make(row[positions["make"]])
        if make in VAG_MAKES:
            make_counts[make] += 1
            if first_vag is None:
                first_vag = {
                    key: row[index].strip()
                    for key, index in positions.items()
                }
    return {
        "encoding": encoding,
        "column_count": len(header),
        "header": header,
        "field_positions_zero_based": positions,
        "complete_data_rows_in_preview": len(data_rows),
        "invalid_row_lengths": invalid,
        "vag_exact_make_counts_in_preview": dict(sorted(make_counts.items())),
        "first_vag_row_sample": first_vag,
        "vag_make_allowlist_exact_only": sorted(VAG_MAKES),
        "documented_row_semantics": "ASTRA TARGA documentation states that one row is emitted for each gearbox variant.",
        "limitations": [
            "Bounded preview only; no full source file or full-source SHA-256.",
            "No rows are imported by this probe.",
            "Getriebe is an ASTRA approval classification, not a confirmed VAG gearbox code.",
            "Motortyp is a raw approval field, not independently confirmed as a VAG factory engine code.",
            "A row preserves a source-defined approval-variant association only; not production vehicle fitment.",
            "CH only; no RU/EAEU applicability, model year or generation is inferred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/astra-targa-emissionen-probe.json")
    args = parser.parse_args()
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "Range": f"bytes=0-{PREVIEW_LIMIT - 1}",
            "Accept-Encoding": "identity",
            "User-Agent": "VAG-TECH-PRO-ASTRA-TARGA-emissionen-probe/1.0",
        },
        method="GET",
    )
    report = {
        "schema_version": 1,
        "probe_kind": "bounded_read_only_schema_probe",
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_id_candidate": "astra-fedro-targa-emissionen-ch",
        "publisher": "Federal Roads Office (FEDRO / ASTRA), Swiss Confederation",
        "market_scope": ["CH"],
        "source_url": SOURCE_URL,
        "data_description_url": DATA_DESCRIPTION_URL,
        "rights_evidence_urls": [ASTRA_OPEN_DATA_URL, ASTRA_VEHICLE_DATA_URL, OGD_POLICY_URL],
        "source_snapshot": {"downloaded": False, "full_file_sha256": None},
    }
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            metadata = {
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "content_range": response.headers.get("Content-Range"),
                "content_length": response.headers.get("Content-Length"),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"),
                "accept_ranges": response.headers.get("Accept-Ranges"),
            }
            if response.status != 206 or not (metadata["content_range"] or "").startswith("bytes 0-"):
                raise ValueError(f"Range response not confirmed: {metadata}")
            raw = response.read(PREVIEW_LIMIT)
            if not raw:
                raise ValueError("Empty range preview")
        report["transport"] = metadata
        report["preview_sha256"] = hashlib.sha256(raw).hexdigest()
        report["preview"] = parse_preview(raw)
        report["probe_status"] = (
            "schema_sample_valid"
            if report["preview"]["complete_data_rows_in_preview"] > 0
            and report["preview"]["invalid_row_lengths"] == 0
            else "schema_sample_inconclusive"
        )
    except Exception as exc:
        report["probe_status"] = "probe_failed"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:2000]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "probe_status": report["probe_status"],
        "transport": report.get("transport"),
        "preview": report.get("preview"),
        "error": report.get("error"),
    }, ensure_ascii=False, indent=2))
    return 0 if report["probe_status"] == "schema_sample_valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
