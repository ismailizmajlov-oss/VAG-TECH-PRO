#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdw_vag_type_approval_common import (
    build_database, sha256_bytes, validate_lock, validate_resource_metadata, verify_pack
)

BASE = "https://opendata.rdw.nl"
PAGE_SIZE = 50000
APPROVAL_BATCH_SIZE = 80
MAX_ROWS_PER_DATASET = 500000
REQUIRED_DATASETS = ["m9d7-ebf2", "4by9-ammk", "7rjk-eycs", "byxc-wwua", "x5v3-sewk"]
MAKE_FILTER = (
    "merk in ('VOLKSWAGEN','VOLKSWAGEN AG','VW','AUDI','AUDI AG',"
    "'SKODA','ŠKODA','SEAT','CUPRA','PORSCHE','BENTLEY','LAMBORGHINI','BUGATTI')"
    " AND europese_voertuigcategorie='M1'"
    " AND voertuigsoort='Personenauto' AND datum_eerste_toelating_dt >= '1998-01-01T00:00:00.000'"
    " AND typegoedkeuringsnummer IS NOT NULL AND variant IS NOT NULL AND uitvoering IS NOT NULL"
)

def request_bytes(url: str, retries: int = 5) -> bytes:
    last_error = None
    for attempt in range(retries):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "VAG-TECH-PRO/0.2.4 RDW CC0 research-pack builder",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
                time.sleep(0.08)
                return payload
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt + 1 == retries:
                body = exc.read(1200).decode("utf-8", "replace")
                raise RuntimeError(f"RDW HTTP {exc.code} for {url}: {body}") from exc
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 20)
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 == retries:
                raise RuntimeError(f"RDW request failed for {url}: {exc}") from exc
            time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"RDW request failed: {last_error}")

def fetch_metadata(dataset_id: str, metadata_gate: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    url = f"{BASE}/api/views/{dataset_id}.json"
    raw = request_bytes(url)
    metadata = json.loads(raw.decode("utf-8"))
    publisher = validate_resource_metadata(dataset_id, metadata, metadata_gate)
    license_values = [
        str(metadata.get(k) or "")
        for k in ("licenseId", "licenseName", "license")
    ]
    joined = " ".join(license_values).strip().lower()
    if joined and not any(x in joined for x in ("cc0", "public domain", "public-domain", "zero")):
        raise ValueError(f"RDW dataset {dataset_id} advertises an unexpected licence: {joined}")
    parsed = {
        "id": dataset_id,
        "name": metadata.get("name") or metadata.get("displayName") or dataset_id,
        "rowsUpdatedAt": metadata.get("rowsUpdatedAt"),
        "metadataUpdatedAt": metadata.get("metadataUpdatedAt"),
        "viewLastModified": metadata.get("viewLastModified"),
        **publisher,
        "metadata_sha256": sha256_bytes(raw),
        "license_metadata": joined or "not_explicit_in_socrata_metadata; covered_by_RDW_open_data_policy_and_parent_CC0_catalogue",
    }
    return parsed, raw

def encode_query(params: list[tuple[str, str]]) -> str:
    return urllib.parse.urlencode(params, quote_via=urllib.parse.quote, safe="(),'")

def fetch_pages(dataset_id: str, base_params: list[tuple[str, str]], batch_number: int,
                next_page_number: int, snapshots: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, list[str]]:
    rows: list[dict[str, Any]] = []
    queries: list[str] = []
    offset = 0
    while True:
        params = list(base_params) + [("$limit", str(PAGE_SIZE)), ("$offset", str(offset))]
        query = encode_query(params)
        url = f"{BASE}/resource/{dataset_id}.json?{query}"
        raw = request_bytes(url)
        page = json.loads(raw.decode("utf-8"))
        if not isinstance(page, list):
            raise ValueError(f"RDW resource {dataset_id} did not return a JSON array")
        if dataset_id == "m9d7-ebf2":
            for row in page:
                keys = {str(k).lower() for k in row}
                if keys.intersection({"kenteken","houder","houdergegevens","tenaamstelling","wam_verzekerd"}):
                    raise ValueError("RDW vehicle query unexpectedly returned a registration/holder field")
        snapshot_name = f"{dataset_id}-batch{batch_number:03d}-page{next_page_number:04d}.json"
        snapshots.append({
            "dataset_id": dataset_id,
            "page_number": next_page_number,
            "request_url": url,
            "response_sha256": sha256_bytes(raw),
            "byte_size": len(raw),
            "row_count": len(page),
            "snapshot_name": snapshot_name,
            "response_bytes": raw,
        })
        rows.extend(page)
        queries.append(url)
        next_page_number += 1
        if len(rows) > MAX_ROWS_PER_DATASET:
            raise ValueError(f"RDW dataset {dataset_id} exceeded the bounded row limit")
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows, next_page_number, queries

def quote_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

def main_query() -> list[tuple[str, str]]:
    select = (
        "merk,handelsbenaming,type,typegoedkeuringsnummer,variant,uitvoering,"
        "min(datum_eerste_toelating_dt) as first_registration_seen,"
        "max(datum_eerste_toelating_dt) as last_registration_seen,"
        "europese_voertuigcategorie,voertuigsoort"
    )
    group = "merk,handelsbenaming,type,typegoedkeuringsnummer,variant,uitvoering,europese_voertuigcategorie,voertuigsoort"
    return [("$select", select), ("$group", group), ("$where", MAKE_FILTER), ("$order", "typegoedkeuringsnummer")]

def approval_query(dataset_id: str, approvals: list[str]) -> list[tuple[str, str]]:
    field = "typegoedkeuringsnummer"
    where = field + " in (" + ",".join(quote_sql(x) for x in approvals) + ")"
    if dataset_id == "byxc-wwua":
        where += " AND voertuigcategorie='M1'"
    select_fields = {
        "4by9-ammk":"typegoedkeuringsnummer,codevarianttgk,codeuitvoeringtgk,volgnummerrevisieuitvoering,volgnummeraandrijving,motorcode,typegoedkeuringsnummermotor,aantalcilinders,cilinderinhoud",
        "7rjk-eycs":"typegoedkeuringsnummer,codevarianttgk,codeuitvoeringtgk,volgnummerrevisieuitvoering,volgnummerversnelling,codetypeversnellingsbak,aantalversnellingenondergrens,aantalversnellingenbovengrens",
        "byxc-wwua":"typegoedkeuringsnummer,codevarianttgk,codeuitvoeringtgk,volgnummerrevisieuitvoering,voertuigcategorie,begindatumrevisieuitvoering,einddatumrevisieuitvoering",
        "x5v3-sewk":"typegoedkeuringsnummer,codevariantgk,codeuitvoeringtgk,volgnummerrevisieuitvoering,volgnummerhandelsbenamingfabr,handelsbenamingfabrikant,typeaanduidingfabrikant",
    }
    return [("$select",select_fields[dataset_id]),("$where", where), ("$order", "typegoedkeuringsnummer")]

def fetch_pack(output_dir: Path, lock_path: Path) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    validate_lock(lock)
    metadata: dict[str, dict[str, Any]] = {}
    metadata_raw: dict[str, bytes] = {}
    for dataset_id in REQUIRED_DATASETS:
        metadata[dataset_id], metadata_raw[dataset_id] = fetch_metadata(dataset_id, lock["live_metadata_gate"])

    snapshots: list[dict[str, Any]] = []
    payloads: dict[str, list[dict[str, Any]]] = {}
    queries: dict[str, str] = {}

    vehicle_rows, next_page, q = fetch_pages("m9d7-ebf2", main_query(), 0, 0, snapshots)
    payloads["m9d7-ebf2"] = vehicle_rows
    queries["m9d7-ebf2"] = "\n".join(q)

    approvals = sorted({str(r.get("typegoedkeuringsnummer","")).strip() for r in vehicle_rows if r.get("typegoedkeuringsnummer")})
    if not approvals:
        raise ValueError("No VAG type-approval numbers were returned by the RDW M1 registration query")

    for dataset_id in REQUIRED_DATASETS[1:]:
        all_rows: list[dict[str, Any]] = []
        all_queries: list[str] = []
        global_page = 0
        for batch_number, start in enumerate(range(0, len(approvals), APPROVAL_BATCH_SIZE)):
            batch = approvals[start:start + APPROVAL_BATCH_SIZE]
            batch_rows, global_page, q = fetch_pages(
                dataset_id, approval_query(dataset_id, batch), batch_number, global_page, snapshots
            )
            all_rows.extend(batch_rows)
            all_queries.extend(q)
        payloads[dataset_id] = all_rows
        queries[dataset_id] = "\n".join(all_queries)

    fetched_at = datetime.now(timezone.utc).isoformat()
    manifest = build_database(output_dir, lock_path, payloads, metadata, snapshots, queries, fetched_at)

    metadata_dir = output_dir / "metadata"
    metadata_dir.mkdir(exist_ok=True)
    metadata_files = []
    for dataset_id, raw in metadata_raw.items():
        path = metadata_dir / f"{dataset_id}-metadata.json"
        path.write_bytes(raw)
        metadata_files.append({"dataset_id":dataset_id,"path":"metadata/"+path.name,"sha256":sha256_bytes(raw),"byte_size":len(raw)})
    metadata_bundle = sha256_bytes("".join(x["sha256"] for x in sorted(metadata_files,key=lambda x:x["dataset_id"])).encode("ascii"))
    manifest["metadata_files"] = metadata_files
    manifest["metadata_bundle_sha256"] = metadata_bundle
    manifest["source_snapshot_sha256"] = manifest["source_snapshot_sha256"]
    (output_dir / "manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    result = verify_pack(output_dir, lock_path)
    if result["status"] != "verified_source_candidate_pack_only":
        raise ValueError("RDW pack verification did not return the expected candidate-only status")
    return manifest

def main() -> int:
    parser = argparse.ArgumentParser(description="Build a rights-cleared RDW VAG type-approval candidate pack")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--lock-path", default="data/source-manifests/rdw-vag-type-approval.lock.json")
    args = parser.parse_args()
    manifest = fetch_pack(Path(args.output_dir), Path(args.lock_path))
    print(json.dumps({
        "status":manifest["verification_status"],
        "source_revision":manifest["source_revision"],
        "counts":manifest["counts"],
        "database_sha256":manifest["database_sha256"],
        "source_snapshot_sha256":manifest["source_snapshot_sha256"],
        "metadata_bundle_sha256":manifest["metadata_bundle_sha256"],
    },ensure_ascii=False,sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
