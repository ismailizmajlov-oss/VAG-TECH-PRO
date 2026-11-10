#!/usr/bin/env python3
"""Probe the public EEA Discodata SQL endpoint with one non-personal VAG row only."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError

from scripts.build_eea_vag_approval_research_pack import (
    api_request,
    map_vag_make,
    reject_personal_fields,
    row_has_key,
    row_value,
)

SAFE_FIELDS = ("MS", "Year", "Status", "Mk", "Cn", "T", "Va", "Ve", "TAN")
TABLE = "[CO2Emission].[latest].[co2cars_2025Pv31]"
QUERY = (
    "SELECT TOP 1 [MS], [Year], [Status], [Mk], [Cn], [T], [Va], [Ve], [TAN] "
    f"FROM {TABLE} WHERE [Year] = 2025 AND [Status] = 'P' "
    "AND [Mk] IN ('AUDI', 'VOLKSWAGEN', 'SKODA', 'SEAT', 'CUPRA') "
    "ORDER BY [MS], [Mk], [Cn], [T], [Va], [Ve], [TAN]"
)
QUERY_SHA256 = hashlib.sha256(QUERY.encode("utf-8")).hexdigest()
HOST = "discodata.eea.europa.eu"


def _network_status(message: str) -> str:
    if re.search(r"HTTP 403\\b", message, re.IGNORECASE):
        return "blocked_http_403"
    if re.search(r"HTTP (?:429|500|502|503|504)\\b", message, re.IGNORECASE):
        return "transient_http_error"
    return "request_rejected"


def probe(api_request_fn: Callable[..., tuple[bytes, dict[str, Any]]] = api_request) -> dict[str, Any]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    try:
        raw, parsed = api_request_fn(QUERY, page=1, page_size=1)
    except RuntimeError as exc:
        return {
            "schema_version": 1,
            "status": _network_status(str(exc)),
            "api_host": HOST,
            "table": TABLE,
            "query_sha256": QUERY_SHA256,
            "response_sha256": None,
            "row_count": 0,
            "retrieved_at_utc": retrieved_at,
            "detail": "No source data acquired; HTTP/network response is not retained.",
        }
    except (TimeoutError, URLError):
        return {
            "schema_version": 1,
            "status": "transient_network_error",
            "api_host": HOST,
            "table": TABLE,
            "query_sha256": QUERY_SHA256,
            "response_sha256": None,
            "row_count": 0,
            "retrieved_at_utc": retrieved_at,
            "detail": "No source data acquired; network response is not retained.",
        }

    rows = parsed.get("results") if isinstance(parsed, dict) else None
    if not isinstance(rows, list) or len(rows) > 1:
        raise ValueError("Discodata probe returned an invalid result array or more than one row.")

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Discodata probe returned a non-object row.")
        reject_personal_fields(row)
        for field in SAFE_FIELDS:
            if not row_has_key(row, field):
                raise ValueError(f"Discodata probe row is missing required field {field}.")
        if int(row_value(row, "Year")) != 2025 or str(row_value(row, "Status")).upper() != "P":
            raise ValueError("Discodata probe row does not match the pinned 2025 provisional scope.")
        if map_vag_make(row_value(row, "Mk")) is None:
            raise ValueError("Discodata probe returned a make outside the exact core VAG allowlist.")

    return {
        "schema_version": 1,
        "status": "reachable" if rows else "reachable_empty",
        "api_host": HOST,
        "table": TABLE,
        "query_sha256": QUERY_SHA256,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "row_count": len(rows),
        "retrieved_at_utc": retrieved_at,
        "detail": "One-row connectivity/schema probe only; row values and raw response are not retained.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = probe()
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
