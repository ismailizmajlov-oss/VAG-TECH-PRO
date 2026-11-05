#!/usr/bin/env python3
"""Probe official ASTRA/FEDRO TAS OGD schema and a small VAG sample; never imports product data."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

BASE = "https://opendata.astra.admin.ch/ivzod/4000-Typengenehmigungen_TAS"
INDEX_URL = BASE + "/4300-Datensaetze/TAS_Personenwagen.xlsb"
SCHEMA_URL = BASE + "/4250-json-Schema/govServices_TypeApproval_Schema.json"
SAMPLES = ("1XZ904", "1XZ734", "1XZ326", "1XZ781", "1XZ516", "1XZ386")
VAG_ALIASES = {"AUDI", "BENTLEY", "BUGATTI", "CUPRA", "LAMBORGHINI", "PORSCHE", "SEAT", "SKODA", "ŠKODA", "VOLKSWAGEN", "VW"}
FIELD_RE = re.compile(r"(engine|motor|gear|transmission|make|brand|type|variant|version|approval|fuel|power|displacement|code|marke|hersteller)", re.I)


def fetch(url: str, path: Path) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "VAG-TECH-PRO/0.1 (offline research source verification)"})
    with urllib.request.urlopen(request, timeout=240) as response:
        data = response.read()
        status = response.status
        final_url = response.geturl()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"url": url, "final_url": final_url, "http_status": status, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def collect_paths(value, prefix=""):
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if FIELD_RE.search(str(key)):
                result.append(path)
            result.extend(collect_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value[:3]):
            result.extend(collect_paths(child, f"{prefix}[{index}]"))
    return result


def collect_values(value, prefix="", out=None):
    if out is None:
        out = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if FIELD_RE.search(str(key)) and not isinstance(child, (dict, list)):
                out.append({"path": path, "value": child})
            collect_values(child, path, out)
    elif isinstance(value, list):
        for index, child in enumerate(value[:20]):
            collect_values(child, f"{prefix}[{index}]", out)
    return out[:120]


def probe_xlsb(path: Path):
    result = {"status": "not_run", "sheets": []}
    try:
        from pyxlsb import open_workbook
        with open_workbook(str(path)) as workbook:
            result["status"] = "ok"
            result["sheet_names"] = list(workbook.sheets)
            for sheet_name in workbook.sheets:
                sheet_result = {"name": sheet_name, "first_rows": [], "vag_match_rows": []}
                with workbook.get_sheet(sheet_name) as sheet:
                    for row_index, row in enumerate(sheet.rows()):
                        values = [cell.v for cell in row]
                        if row_index < 12:
                            sheet_result["first_rows"].append(values)
                        if len(sheet_result["vag_match_rows"]) < 40:
                            normalized = {str(v).strip().upper() for v in values if v is not None}
                            if normalized & VAG_ALIASES:
                                sheet_result["vag_match_rows"].append({"row_index": row_index, "values": values})
                        if row_index >= 250000:
                            sheet_result["scan_limit_reached"] = True
                            break
                result["sheets"].append(sheet_result)
    except Exception as exc:
        result["status"] = "parse_error"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    cache = out / "downloaded"
    cache.mkdir(parents=True, exist_ok=True)
    report = {
        "source_id": "astra-fedro-tas-type-approvals-open-data-ch",
        "market_scope": "CH",
        "data_snapshot": "2026-10-29",
        "rights": "Swiss OGD; FEDRO attribution required",
        "downloads": {},
        "schema": {},
        "sample_records": [],
    }

    index_path = cache / "TAS_Personenwagen.xlsb"
    report["downloads"]["passenger_car_index"] = fetch(INDEX_URL, index_path)
    report["workbook_probe"] = probe_xlsb(index_path)

    schema_path = cache / "govServices_TypeApproval_Schema.json"
    report["downloads"]["json_schema"] = fetch(SCHEMA_URL, schema_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    report["schema"] = {
        "top_level_keys": list(schema.keys()) if isinstance(schema, dict) else [],
        "relevant_paths": sorted(set(collect_paths(schema)))[:500],
    }

    for approval in SAMPLES:
        url = f"{BASE}/4100-json-Files/MV_{approval}.json"
        record_path = cache / f"MV_{approval}.json"
        try:
            metadata = fetch(url, record_path)
            payload = json.loads(record_path.read_text(encoding="utf-8-sig"))
            report["sample_records"].append({
                "approval": approval,
                "download": metadata,
                "top_level_keys": list(payload.keys()) if isinstance(payload, dict) else [],
                "relevant_paths": sorted(set(collect_paths(payload)))[:500],
                "relevant_values": collect_values(payload),
            })
        except Exception as exc:
            report["sample_records"].append({
                "approval": approval,
                "url": url,
                "status": "probe_error",
                "error": f"{type(exc).__name__}: {exc}",
            })

    successful = sum(1 for item in report["sample_records"] if "download" in item)
    report["sample_success_count"] = successful
    report["probe_status"] = "completed" if successful else "no_sample_records_downloaded"
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "astra-ch-tas-schema-probe.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "probe_status": report["probe_status"],
        "sample_success_count": successful,
        "index_sha256": report["downloads"]["passenger_car_index"]["sha256"],
        "schema_sha256": report["downloads"]["json_schema"]["sha256"],
        "workbook_probe_status": report["workbook_probe"]["status"],
        "report": str(report_path),
    }, ensure_ascii=False))
    if successful == 0:
        raise SystemExit("No sample ASTRA JSON records could be verified.")


if __name__ == "__main__":
    main()
