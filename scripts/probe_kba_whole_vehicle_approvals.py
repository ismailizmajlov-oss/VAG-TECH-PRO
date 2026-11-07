#!/usr/bin/env python3
"""Read-only probe for the KBA whole-vehicle type-approval XLSX.

The GovData record explicitly publishes this dataset under DL-DE BY 2.0.
This probe downloads only the official KBA resource, verifies the XLSX
container, records SHA-256 and inspects workbook/sheet headers. It never
imports rows into the production or research SQLite database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_ID = "kba-de-whole-vehicle-type-approvals"
SOURCE_URL = (
    "https://www.kba.de/DE/Themen/Typgenehmigung/Informationen_TGV/"
    "Liste_erteilter_Typgenehmigungen/"
    "liste_typgenehmigungen_Excel.xlsx?__blob=publicationFile&v=13"
)
GOVDATA_URL = (
    "https://www.govdata.de/suche/daten/"
    "liste-der-erteilten-typgenehmigungen-gesamtfahrzeug"
    "?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb"
)
LICENSE_URL = "https://www.govdata.de/dl-de/by-2-0"
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_ZIP_ENTRIES = 2000
TIMEOUT_SECONDS = 35
HEADER_HINTS = ("hersteller", "manufacturer", "marke", "handelsname", "typbezeichnung", "typgenehmigungsnummer", "genehmigungsnummer", "approval number")
NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_official_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"www.kba.de", "kba.de"}:
        raise ValueError("KBA probe accepts only the official HTTPS KBA host")
    if not parsed.path.lower().endswith(".xlsx"):
        raise ValueError("KBA approval resource must be an XLSX URL")


def _safe_zip_member(name: str) -> str:
    normalized = posixpath.normpath(name.replace("\\", "/"))
    if normalized.startswith("../") or normalized in {"..", "."} or normalized.startswith("/"):
        raise ValueError("unsafe XLSX archive member path")
    return normalized


def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    if not letters:
        raise ValueError("invalid XLSX cell reference")
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - 64
    return value - 1


def parse_xlsx_headers(payload: bytes) -> dict[str, Any]:
    if not payload.startswith(b"PK\x03\x04"):
        raise ValueError("download is not an XLSX ZIP container")
    import io

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            raise ValueError("XLSX archive contains too many entries")
        total_uncompressed = sum(item.file_size for item in infos)
        if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("XLSX archive exceeds the uncompressed-size limit")
        for item in infos:
            _safe_zip_member(item.filename)
            if item.file_size > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("XLSX member exceeds the uncompressed-size limit")
            if item.compress_size and item.file_size / item.compress_size > 250:
                raise ValueError("XLSX member has an unsafe compression ratio")
        if archive.testzip() is not None:
            raise ValueError("XLSX archive CRC validation failed")

        names = { _safe_zip_member(item.filename) for item in infos }
        if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
            raise ValueError("XLSX workbook parts are missing")

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_targets: dict[str, str] = {}
        for rel in relationships.findall("pkgrel:Relationship", NS):
            if rel.attrib.get("TargetMode", "").lower() == "external":
                continue
            rel_id = rel.attrib.get("Id")
            target = rel.attrib.get("Target", "")
            if not rel_id or not target:
                continue
            if target.startswith("/"):
                resolved = posixpath.normpath(target.lstrip("/"))
            else:
                resolved = posixpath.normpath(posixpath.join("xl", target))
            if resolved.startswith("../") or resolved not in names:
                raise ValueError("workbook relationship points outside the XLSX archive")
            rel_targets[rel_id] = resolved

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("main:si", NS):
                shared_strings.append("".join(
                    node.text or "" for node in item.findall(".//main:t", NS)
                ))

        sheets: list[dict[str, Any]] = []
        for sheet in workbook.findall("main:sheets/main:sheet", NS):
            name = sheet.attrib.get("name", "")
            rel_id = sheet.attrib.get("{" + NS["rel"] + "}id", "")
            target = rel_targets.get(rel_id)
            if not target:
                continue
            root = ET.fromstring(archive.read(target))
            rows = root.findall(".//main:sheetData/main:row", NS)
            nonempty_rows: list[tuple[int, list[str]]] = []
            for row in rows[:30]:
                values: dict[int, str] = {}
                for cell in row.findall("main:c", NS):
                    ref = cell.attrib.get("r", "")
                    col = _column_index(ref)
                    cell_type = cell.attrib.get("t", "")
                    value_node = cell.find("main:v", NS)
                    value = value_node.text if value_node is not None and value_node.text is not None else ""
                    if cell_type == "s" and value:
                        shared_index = int(value)
                        if shared_index < 0 or shared_index >= len(shared_strings):
                            raise ValueError("XLSX shared-string index is out of range")
                        value = shared_strings[shared_index]
                    elif cell_type == "inlineStr":
                        value = "".join(node.text or "" for node in cell.findall(".//main:t", NS))
                    values[col] = value
                if values:
                    width = max(values) + 1
                    row_number = int(row.attrib.get("r", len(nonempty_rows) + 1))
                    nonempty_rows.append((row_number, [values.get(i, "") for i in range(width)]))
            if not nonempty_rows:
                sheets.append({"name": name, "header": [], "sample_rows": [], "header_status": "no_nonempty_rows"})
                continue

            def header_score(values: list[str]) -> int:
                normalized = [str(value).strip().casefold() for value in values]
                return sum(1 for hint in HEADER_HINTS if any(hint in cell for cell in normalized))

            candidates = [(header_score(values), index) for index, (_, values) in enumerate(nonempty_rows)]
            score, header_index = max(candidates, default=(0, 0))
            if score >= 2:
                header_status = "candidate_header_by_known_field_names"
            else:
                header_index = 0
                header_status = "unconfirmed_first_nonempty_row"
            header_row_number, header_values = nonempty_rows[header_index]
            header = [str(value).strip() for value in header_values]
            samples = [values for _, values in nonempty_rows[header_index + 1:header_index + 3]]
            sheets.append({
                "name": name,
                "header_row_number": header_row_number,
                "header_status": header_status,
                "header_match_score": score,
                "header": header,
                "sample_rows": samples,
            })
        if not sheets:
            raise ValueError("XLSX workbook contains no readable worksheets")
        return {"sheet_count": len(sheets), "sheets": sheets}


def fetch_resource(url: str) -> dict[str, Any]:
    validate_official_url(url)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VAG-TECH-PRO-KBA-approval-probe/1.0 (+https://github.com/ismailizmajlov-oss/VAG-TECH-PRO)",
            "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            validate_official_url(final_url)
            status = getattr(response, "status", 200)
            headers = dict(response.headers.items())
            body = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(body) > MAX_DOWNLOAD_BYTES:
                return {
                    "url": url, "final_url": final_url, "status": status,
                    "content_type": headers.get("Content-Type"),
                    "error": "response_exceeded_50_mib_probe_limit",
                    "bytes_read": len(body),
                }
            return {
                "url": url, "final_url": final_url, "status": status,
                "content_type": headers.get("Content-Type"),
                "last_modified": headers.get("Last-Modified"),
                "etag": headers.get("ETag"),
                "body": body, "sha256": sha256(body), "bytes": len(body),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(4096)
        return {
            "url": url, "status": exc.code,
            "content_type": exc.headers.get("Content-Type"),
            "error": f"HTTP_{exc.code}",
            "error_body_sha256": sha256(body),
            "error_excerpt": body[:500].decode("utf-8", "replace"),
        }
    except Exception as exc:
        return {"url": url, "status": None, "error": f"{type(exc).__name__}: {exc}"}


def run_probe(out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    result = fetch_resource(SOURCE_URL)
    body = result.pop("body", None)
    workbook: dict[str, Any] | None = None
    if isinstance(body, bytes):
        try:
            workbook = parse_xlsx_headers(body)
            (out_dir / "kba-whole-vehicle-type-approvals.xlsx").write_bytes(body)
            status = "resource_acquired_schema_available"
        except Exception as exc:
            result["xlsx_validation_error"] = f"{type(exc).__name__}: {exc}"
            status = "resource_retrieved_but_schema_validation_failed"
    else:
        status = "official_resource_unavailable"
    report = {
        "schema_version": 1,
        "source_id": SOURCE_ID,
        "publisher": "Kraftfahrt-Bundesamt (KBA), Germany",
        "market_scope": ["DE"],
        "source_url": SOURCE_URL,
        "catalog_url": GOVDATA_URL,
        "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0)",
        "license_url": LICENSE_URL,
        "rights_evidence": "GovData dataset page explicitly marks the resource as freie Nutzung under DL-DE BY 2.0.",
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "probe_only": True,
        "product_import_allowed": False,
        "data_ingested": False,
        "production_fitment": False,
        "ru_eaeu_applicability": False,
        "exact_engine_gearbox_pair": False,
        "status": status,
        "resource": result,
        "workbook_schema": workbook,
        "limitations": [
            "The source is a German KBA whole-vehicle type-approval list, not a vehicle build sheet.",
            "No engine/gearbox pair, model year, generation, ECU, DTC or repair applicability is inferred.",
            "No Russian/EAEU applicability is inferred.",
            "The probe does not write to SQLite or change product import approval.",
            "Source rows must be independently checked for exact manufacturer and approval-scope fields before any research-pack build.",
        ],
    }
    (out_dir / "probe-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="kba-whole-approvals-probe-out")
    args = parser.parse_args()
    report = run_probe(Path(args.out))
    print(json.dumps({
        "status": report["status"],
        "source_id": report["source_id"],
        "market_scope": report["market_scope"],
        "resource": {k: v for k, v in report["resource"].items() if k != "error_excerpt"},
        "sheet_count": report["workbook_schema"]["sheet_count"] if report["workbook_schema"] else None,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
