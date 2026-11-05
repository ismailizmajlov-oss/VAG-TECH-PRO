#!/usr/bin/env python3
"""Probe official ASTRA/FEDRO TAS OGD schema and a small VAG sample; never imports product data."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

BASE = "https://opendata.astra.admin.ch/ivzod/4000-Typengenehmigungen_TAS"
INDEXES = {
    "passenger_cars": BASE + "/4300-Datensaetze/TAS_Personenwagen.xlsb",
    "other_automobiles": BASE + "/4300-Datensaetze/TAS_restliche_Automobilgruppen.xlsb",
    "emissions": BASE + "/4300-Datensaetze/TAS_Emission.xlsb",
}
SCHEMA_URL = BASE + "/4250-json-Schema/govServices_TypeApproval_Schema.json"
SAMPLES = ("1XZ904", "1XZ734", "1XZ326", "1XZ781", "1XZ516", "1XZ386")
VAG_ALIASES = {"AUDI", "BENTLEY", "BUGATTI", "CUPRA", "LAMBORGHINI", "PORSCHE", "SEAT", "SKODA", "ŠKODA", "VOLKSWAGEN", "VW"}
FIELD_RE = re.compile(r"(engine|motor|gear|transmission|make|brand|type|variant|version|approval|fuel|power|displacement|code|marke|hersteller)", re.I)
MAX_SCAN_ROWS = 300000


def fetch(url: str, path: Path) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "VAG-TECH-PRO/0.1 (offline research source verification)"})
    with urllib.request.urlopen(request, timeout=240) as response:
        status = response.status
        final_url = response.geturl()
        digest = hashlib.sha256()
        size = 0
        with path.open("wb") as stream:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                stream.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    return {"url": url, "final_url": final_url, "http_status": status, "size_bytes": size, "sha256": digest.hexdigest()}


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
    return out[:160]


def compact_row(header, values):
    if not header:
        return values[:20]
    wanted = {
        "chTypeApprovalNumber", "makeName", "commercialName", "type", "variant", "version",
        "manufacturerOfTheEngine", "engineType", "chEngineCodeAsMarkedOnTheEngine",
        "chFuelType", "engineCapacity", "maximumNetPower",
        "gearboxEmissions1.chGearboxType", "gearboxEmissions2.chGearboxType",
        "gearboxEmissions3.chGearboxType", "gearboxEmissions4.chGearboxType",
    }
    return {header[i]: values[i] if i < len(values) else None for i in range(len(header)) if header[i] in wanted}


def probe_xlsb(path: Path, match_approvals=False):
    result = {"status": "not_run", "sheets": []}
    try:
        from pyxlsb import open_workbook
        with open_workbook(str(path)) as workbook:
            result["status"] = "ok"
            result["sheet_names"] = list(workbook.sheets)
            for sheet_name in workbook.sheets:
                sheet_result = {"name": sheet_name, "first_rows": [], "vag_make_counts": {}, "vag_match_samples": [], "approval_match_rows": []}
                make_counts = Counter()
                samples_by_make = defaultdict(list)
                rows_scanned = 0
                with workbook.get_sheet(sheet_name) as sheet:
                    header = None
                    make_index = None
                    approval_index = None
                    for row_index, row in enumerate(sheet.rows()):
                        values = [cell.v for cell in row]
                        rows_scanned += 1
                        if row_index < 4:
                            sheet_result["first_rows"].append(values)
                        if header is None and any(v is not None for v in values):
                            header = [str(v) if v is not None else "" for v in values]
                            sheet_result["header"] = header
                            make_index = header.index("makeName") if "makeName" in header else None
                            approval_index = header.index("chTypeApprovalNumber") if "chTypeApprovalNumber" in header else None
                        if match_approvals:
                            joined = {str(v).strip().upper() for v in values if v is not None}
                            if joined.intersection(SAMPLES) and len(sheet_result["approval_match_rows"]) < 60:
                                sheet_result["approval_match_rows"].append({"row_index": row_index, "values": compact_row(header, values)})
                        elif make_index is not None and make_index < len(values):
                            make = str(values[make_index] or "").strip().upper()
                            if make in VAG_ALIASES:
                                make_counts[make] += 1
                                if len(samples_by_make[make]) < 5:
                                    samples_by_make[make].append({"row_index": row_index, "values": compact_row(header, values)})
                        if row_index + 1 >= MAX_SCAN_ROWS:
                            sheet_result["scan_limit_reached"] = True
                            break
                sheet_result["rows_scanned"] = rows_scanned
                sheet_result["vag_make_counts"] = dict(sorted(make_counts.items()))
                sheet_result["vag_match_samples"] = [item for make in sorted(samples_by_make) for item in samples_by_make[make]]
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
        "workbook_probes": {},
        "schema": {},
        "sample_records": [],
    }

    for name, url in INDEXES.items():
        path = cache / (name + ".xlsb")
        print(f"Downloading {name} index: {url}", flush=True)
        report["downloads"][name] = fetch(url, path)
        print(f"Downloaded {name}: {report['downloads'][name]['size_bytes']} bytes; sha256={report['downloads'][name]['sha256']}", flush=True)
        report["workbook_probes"][name] = probe_xlsb(path, match_approvals=(name == "emissions"))
        print(f"Parsed {name}: {report['workbook_probes'][name]['status']}", flush=True)

    schema_path = cache / "govServices_TypeApproval_Schema.json"
    report["downloads"]["json_schema"] = fetch(SCHEMA_URL, schema_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    report["schema"] = {
        "top_level_keys": list(schema.keys()) if isinstance(schema, dict) else [],
        "relevant_paths": sorted(set(collect_paths(schema)))[:1000],
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
                "relevant_paths": sorted(set(collect_paths(payload)))[:1000],
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
        "downloads": {k: {"size_bytes": v["size_bytes"], "sha256": v["sha256"]} for k,v in report["downloads"].items()},
        "workbook_statuses": {k: v["status"] for k,v in report["workbook_probes"].items()},
        "report": str(report_path),
    }, ensure_ascii=False))
    if successful == 0:
        raise SystemExit("No sample ASTRA JSON records could be verified.")


if __name__ == "__main__":
    main()
