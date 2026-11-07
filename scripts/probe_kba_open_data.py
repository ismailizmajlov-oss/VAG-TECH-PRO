#!/usr/bin/env python3
"""Probe public KBA/ArcGIS delivery paths without importing any data.

The probe is deliberately read-only. It retrieves only public catalogue metadata,
service schema and (if available) one public sample row. A complete CSV download is
accepted only from the explicitly licensed KBA dataset endpoint and is retained as
an internal CI artifact for a later schema/provenance review; it is never imported
into the product database by this script.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ITEM_ID = "d277ec18ff1e442597c9411d7c1aaeaa"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
TIMEOUT_SECONDS = 35
EXACT_VAG_MANUFACTURER_LABELS = {
    "volkswagen (d)", "audi (d)", "audi (h)", "skoda (cz)", "seat (e)",
    "porsche", "bentley (uk)", "lamborghini (i)",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def exact_vag_manufacturer_values(values: list[str]) -> list[str]:
    """Return only exact normalized allowlist matches; never substring/fuzzy matches."""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        raw = str(value).strip()
        normalized = re.sub(r"\s+", " ", raw).casefold()
        if normalized in EXACT_VAG_MANUFACTURER_LABELS and normalized not in seen:
            result.append(raw)
            seen.add(normalized)
    return result


def parse_csv_payload(payload: bytes) -> dict[str, Any] | None:
    filename = "source.csv"
    csv_bytes = payload
    if payload[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                candidates = [n for n in archive.namelist() if n.lower().endswith(".csv")]
                if not candidates:
                    return None
                filename = candidates[0]
                csv_bytes = archive.read(filename)
        except (zipfile.BadZipFile, KeyError):
            return None
    try:
        text = csv_bytes.decode("utf-8-sig")
        if text.lstrip().startswith(("{", "[")):
            try:
                json.loads(text)
                return None
            except json.JSONDecodeError:
                pass
        first_line = text.splitlines()[0] if text.splitlines() else ""
        delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        fields = list(reader.fieldnames or [])
        if not fields:
            return None
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error):
        return None
    manufacturer_fields = [
        f for f in fields
        if any(token in f.casefold() for token in ("hersteller", "manufacturer", "marke"))
    ]
    exact_values: list[str] = []
    for field in manufacturer_fields:
        exact_values.extend(
            str(row.get(field, ""))
            for row in rows
            if row.get(field) not in (None, "")
        )
    return {
        "filename": filename,
        "columns": fields,
        "row_count": len(rows),
        "manufacturer_field_candidates": manufacturer_fields,
        "exact_vag_manufacturer_values": exact_vag_manufacturer_values(exact_values),
        "sample_rows": rows[:3],
        "csv_sha256": sha256(csv_bytes),
        "csv_bytes": len(csv_bytes),
    }


def fetch(url: str, *, max_bytes: int = MAX_DOWNLOAD_BYTES) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VAG-TECH-PRO-KBA-public-source-probe/1.0 (+https://github.com/ismailizmajlov-oss/VAG-TECH-PRO)",
            "Accept": "application/json,text/csv,application/zip,application/octet-stream,*/*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", 200)
            headers = dict(response.headers.items())
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                return {
                    "url": url,
                    "status": status,
                    "content_type": headers.get("Content-Type"),
                    "error": f"response_exceeded_{max_bytes}_byte_probe_limit",
                    "bytes_read": len(body),
                }
            return {
                "url": url,
                "status": status,
                "content_type": headers.get("Content-Type"),
                "content_length": headers.get("Content-Length"),
                "body": body,
                "sha256": sha256(body),
                "bytes": len(body),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(4096)
        return {
            "url": url,
            "status": exc.code,
            "content_type": exc.headers.get("Content-Type"),
            "error": f"HTTP_{exc.code}",
            "error_body_sha256": sha256(body),
            "error_excerpt": body[:500].decode("utf-8", "replace"),
        }
    except Exception as exc:
        return {"url": url, "status": None, "error": f"{type(exc).__name__}: {exc}"}


def json_body(result: dict[str, Any]) -> dict[str, Any] | None:
    body = result.get("body")
    if not isinstance(body, bytes):
        return None
    try:
        value = json.loads(body.decode("utf-8-sig"))
        return value if isinstance(value, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def query_url(service_url: str, layer_id: int) -> str:
    base = service_url.rstrip("/")
    if not re.search(r"/(FeatureServer|MapServer)$", base, re.I):
        raise ValueError("not_an_arcgis_feature_or_map_service_url")
    params = urllib.parse.urlencode({
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "false",
        "resultRecordCount": "1",
        "f": "json",
    })
    return f"{base}/{layer_id}/query?{params}"


def summarize_json_service(payload: dict[str, Any]) -> dict[str, Any]:
    if "error" in payload:
        return {"service_error": payload["error"]}
    fields = payload.get("fields") or []
    features = payload.get("features") or []
    sample = features[0].get("attributes", {}) if features else {}
    return {
        "field_names": [f.get("name") for f in fields if isinstance(f, dict)],
        "field_definitions": fields,
        "sample_row": sample,
        "sample_row_count": len(features),
        "exceeded_transfer_limit": payload.get("exceededTransferLimit", False),
    }


def run_probe(out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    item_url = f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}?f=pjson"
    item_result = fetch(item_url, max_bytes=2 * 1024 * 1024)
    attempts.append({k: v for k, v in item_result.items() if k != "body"})
    item = json_body(item_result) or {}

    hub_metadata_url = f"https://hub.arcgis.com/api/v3/datasets/{ITEM_ID}"
    hub_result = fetch(hub_metadata_url, max_bytes=4 * 1024 * 1024)
    attempts.append({k: v for k, v in hub_result.items() if k != "body"})

    service_url = item.get("url") if isinstance(item.get("url"), str) else None
    service_summary = None
    if service_url and re.search(r"/(FeatureServer|MapServer)$", service_url, re.I):
        service_meta = fetch(f"{service_url.rstrip('/')}?f=pjson", max_bytes=4 * 1024 * 1024)
        attempts.append({k: v for k, v in service_meta.items() if k != "body"})
        service = json_body(service_meta) or {}
        layers = service.get("layers") or service.get("tables") or []
        if layers and isinstance(layers[0], dict) and isinstance(layers[0].get("id"), int):
            layer_id = layers[0]["id"]
            q = fetch(query_url(service_url, layer_id), max_bytes=4 * 1024 * 1024)
            attempts.append({k: v for k, v in q.items() if k != "body"})
            query_payload = json_body(q)
            if query_payload:
                service_summary = summarize_json_service(query_payload)

    download_urls = [
        f"https://hub.arcgis.com/api/v3/datasets/{ITEM_ID}/files/4326/csv?where=1%3D1",
        f"https://hub.arcgis.com/api/download/v1/items/{ITEM_ID}/csv?layers=0",
        f"https://hub.arcgis.com/api/download/v1/items/{ITEM_ID}/csv?layers=0&where=1%3D1",
    ]
    acquired: dict[str, Any] | None = None
    parsed: dict[str, Any] | None = None
    for url in download_urls:
        result = fetch(url)
        attempts.append({k: v for k, v in result.items() if k != "body"})
        body = result.get("body")
        if isinstance(body, bytes):
            parsed = parse_csv_payload(body)
            if parsed:
                acquired = {
                    "url": url,
                    "sha256": sha256(body),
                    "bytes": len(body),
                    "content_type": result.get("content_type"),
                }
                filename = "source-download.zip" if body[:4] == b"PK\x03\x04" else "source-download.csv"
                (out_dir / filename).write_bytes(body)
                break

    report = {
        "schema_version": 1,
        "source_id": "kba-de-fz-hersteller-handelsnamen-pkw",
        "item_id": ITEM_ID,
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "probe_only": True,
        "product_import_allowed": False,
        "data_ingested": False,
        "rights_basis": "GovData explicitly lists DL-DE BY 2.0; attribution and modification notice required.",
        "item_metadata": {
            key: item.get(key)
            for key in ("id", "title", "type", "url", "modified", "licenseInfo", "accessInformation")
            if key in item
        },
        "hub_metadata_sha256": hub_result.get("sha256"),
        "service_schema_probe": service_summary,
        "download": acquired,
        "csv_schema": parsed,
        "attempts": attempts,
        "status": "resource_acquired_schema_available" if acquired else (
            "service_schema_available_only" if service_summary else "metadata_or_endpoint_probe_only"
        ),
        "limitations": [
            "No row is promoted to VAG exact fitment.",
            "HSN/TSN are German registration identity keys, not engine/gearbox codes.",
            "Annual reference date is not model year or generation.",
            "No RU/EAEU applicability is inferred.",
            "This probe does not write to SQLite or change product source approval.",
        ],
    }
    (out_dir / "probe-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="kba-probe-out")
    args = parser.parse_args()
    report = run_probe(Path(args.out))
    print(json.dumps({
        "status": report["status"],
        "download": report["download"],
        "service_schema_available": report["service_schema_probe"] is not None,
        "attempts": [
            {"url": attempt["url"], "status": attempt.get("status"), "error": attempt.get("error")}
            for attempt in report["attempts"]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
