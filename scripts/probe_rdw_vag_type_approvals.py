#!/usr/bin/env python3
"""Probe official RDW VAG type-approval data without importing a product snapshot.

Only a small, filtered sample is queried. Registration identifiers and holder data
are excluded by an explicit $select allowlist. Engine and gearbox rows remain
separate; this probe never creates a powertrain pair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = "https://opendata.rdw.nl"
SOURCE_ID = "rdw-eu-vag-type-approval-open-data-nl"
MANIFEST_PATH = Path("data/source-manifests/rdw-eu-vag-type-approval-open-data.json")
VEHICLE_DATASET = "m9d7-ebf2"
VAG_MAKE = "VOLKSWAGEN"
VEHICLE_FIELDS = [
    "merk", "handelsbenaming", "typegoedkeuringsnummer", "variant",
    "uitvoering", "volgnummer_wijziging_eu_typegoedkeuring",
    "datum_eerste_toelating", "voertuigsoort", "cilinderinhoud", "aantal_cilinders",
]
FORBIDDEN_FIELD_TOKENS = ("kenteken", "vin", "houder", "owner", "tenaamstelling")
DATASETS = {
    "tgk_drive": {
        "id": "4by9-ammk",
        "required": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "motorcode", "typegoedkeuringsnummermotor",
                     "aantalcilinders", "cilinderinhoud"],
        "variant_field": "codevarianttgk",
        "select": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "motorcode", "typegoedkeuringsnummermotor", "aantalcilinders", "cilinderinhoud"],
    },
    "tgk_gearbox": {
        "id": "7rjk-eycs",
        "required": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "codetypeversnellingsbak"],
        "variant_field": "codevarianttgk",
        "select": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "codetypeversnellingsbak"],
    },
    "tgk_base": {
        "id": "byxc-wwua",
        "required": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "begindatumrevisieuitvoering", "voertuigcategorie"],
        "variant_field": "codevarianttgk",
        "select": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "begindatumrevisieuitvoering", "voertuigcategorie"],
    },
    "tgk_make": {
        "id": "kyri-nuah",
        "required": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "merkcoderdw"],
        "variant_field": "codevarianttgk",
        "select": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "merkcoderdw"],
    },
    "tgk_trade_name": {
        "id": "x5v3-sewk",
        "required": ["typegoedkeuringsnummer", "codevariantgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "handelsbenamingfabrikant", "typeaanduidingfabrikant"],
        "variant_field": "codevariantgk",
        "select": ["typegoedkeuringsnummer", "codevariantgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "handelsbenamingfabrikant", "typeaanduidingfabrikant"],
    },
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def build_soda_url(dataset_id: str, params: dict[str, str]) -> str:
    if not dataset_id or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in dataset_id):
        raise ValueError("Invalid RDW dataset id")
    return f"{BASE}/resource/{dataset_id}.json?{urllib.parse.urlencode(params)}"


def fetch_json(url: str, *, attempts: int = 4) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "VAG-TECH-PRO-RDW-source-probe/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 200:
                    raise RuntimeError(f"RDW HTTP {response.status}: {url}")
                raw = response.read(32 * 1024 * 1024 + 1)
                if len(raw) > 32 * 1024 * 1024:
                    raise RuntimeError("RDW probe response exceeded 32 MiB limit")
                return json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"RDW request failed after {attempts} attempts: {last_error}") from last_error


def metadata_columns(metadata: dict[str, Any]) -> set[str]:
    columns = set()
    for item in metadata.get("columns", []):
        name = item.get("fieldName") or item.get("name")
        if name:
            columns.add(str(name))
    return columns


def fetch_metadata(dataset_id: str) -> dict[str, Any]:
    return fetch_json(f"{BASE}/api/views/{dataset_id}.json")


def soql_literal(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def registration_scope_key(row: dict[str, Any]) -> dict[str, str]:
    return {
        "typegoedkeuringsnummer": str(row.get("typegoedkeuringsnummer") or ""),
        "variant": str(row.get("variant") or ""),
        "uitvoering": str(row.get("uitvoering") or ""),
        "revision": str(row.get("volgnummer_wijziging_eu_typegoedkeuring") or ""),
    }


def exact_scope_where(key: dict[str, str], variant_field: str) -> str:
    if variant_field not in {"codevarianttgk", "codevariantgk"}:
        raise ValueError("Unapproved RDW variant field")
    required = ("typegoedkeuringsnummer", "variant", "uitvoering", "revision")
    if any(not key.get(name) for name in required):
        raise ValueError("Incomplete exact RDW approval scope key")
    return (
        f"typegoedkeuringsnummer={soql_literal(key['typegoedkeuringsnummer'])} AND "
        f"{variant_field}={soql_literal(key['variant'])} AND "
        f"codeuitvoeringtgk={soql_literal(key['uitvoering'])} AND "
        f"volgnummerrevisieuitvoering={soql_literal(key['revision'])}"
    )


def select_nonidentifying_fields(row: dict[str, Any]) -> dict[str, Any]:
    selected = {name: row.get(name) for name in VEHICLE_FIELDS if name in row}
    lowered = {str(name).lower() for name in selected}
    if any(any(token in name for token in FORBIDDEN_FIELD_TOKENS) for name in lowered):
        raise ValueError("Forbidden registration or personal-data field selected")
    return selected


def filter_exact_scope(rows: list[dict[str, Any]], key: dict[str, str], variant_field: str) -> list[dict[str, Any]]:
    expected = {
        "typegoedkeuringsnummer": key["typegoedkeuringsnummer"],
        variant_field: key["variant"],
        "codeuitvoeringtgk": key["uitvoering"],
        "volgnummerrevisieuitvoering": key["revision"],
    }
    return [row for row in rows if all(str(row.get(field) or "") == value for field, value in expected.items())]


def query_rows(dataset_id: str, *, select: list[str], where: str, limit: int = 100, order: str | None = None) -> list[dict[str, Any]]:
    params = {"$select": ",".join(select), "$where": where, "$limit": str(limit)}
    if order:
        params["$order"] = order
    result = fetch_json(build_soda_url(dataset_id, params))
    if not isinstance(result, list):
        raise RuntimeError(f"Unexpected RDW response for {dataset_id}")
    for row in result:
        if not isinstance(row, dict):
            raise RuntimeError(f"Non-object RDW row in {dataset_id}")
        if any(any(token in str(key).lower() for token in FORBIDDEN_FIELD_TOKENS) for key in row):
            raise RuntimeError(f"Forbidden field returned by RDW query {dataset_id}")
    return result


def probe(output_dir: Path) -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("source_id") != SOURCE_ID or manifest.get("rights", {}).get("rights_status") != "approved_by_published_CC0_license":
        raise RuntimeError("RDW source manifest identity or rights gate failed")
    manifest_sha = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()

    metadata_reports = {}
    required_by_dataset = {
        VEHICLE_DATASET: set(VEHICLE_FIELDS),
        **{cfg["id"]: set(cfg["required"]) for cfg in DATASETS.values()},
    }
    for dataset_id, required in required_by_dataset.items():
        metadata = fetch_metadata(dataset_id)
        columns = metadata_columns(metadata)
        missing = sorted(required - columns)
        if missing:
            raise RuntimeError(f"RDW dataset {dataset_id} missing required columns: {missing}")
        metadata_reports[dataset_id] = {
            "rows_updated_at": metadata.get("rowsUpdatedAt"),
            "view_last_modified": metadata.get("viewLastModified"),
            "columns_sha256": sha256_json(sorted(columns)),
            "required_columns_verified": sorted(required),
            "required_columns_missing": [],
        }
        time.sleep(0.2)

    where = (
        f"merk={soql_literal(VAG_MAKE)} AND typegoedkeuringsnummer IS NOT NULL AND "
        f"voertuigsoort={soql_literal('Personenauto')} AND cilinderinhoud > 0"
    )
    vehicle_rows = query_rows(VEHICLE_DATASET, select=VEHICLE_FIELDS, where=where, limit=250, order="datum_eerste_toelating DESC")
    if not vehicle_rows:
        raise RuntimeError("RDW returned no Volkswagen passenger-car approval observations")
    vehicle_rows.sort(key=lambda row: str(row.get("datum_eerste_toelating") or ""), reverse=True)

    chosen = None
    matched = {}
    attempted_keys = set()
    for raw_row in vehicle_rows[:25]:
        row = select_nonidentifying_fields(raw_row)
        key = registration_scope_key(row)
        if any(not key[name] for name in ("typegoedkeuringsnummer", "variant", "uitvoering", "revision")):
            continue
        key_token = tuple(key[name] for name in ("typegoedkeuringsnummer", "variant", "uitvoering", "revision"))
        if key_token in attempted_keys:
            continue
        attempted_keys.add(key_token)
        current = {}
        for name, cfg in DATASETS.items():
            where = exact_scope_where(key, cfg["variant_field"])
            rows = query_rows(cfg["id"], select=cfg["select"], where=where, limit=200)
            current[name] = filter_exact_scope(rows, key, cfg["variant_field"])
            time.sleep(0.12)
        if current["tgk_base"] and current["tgk_drive"] and current["tgk_gearbox"]:
            chosen = row
            matched = current
            break

    if chosen is None:
        raise RuntimeError("No exact Volkswagen approval variant/version/revision scope was found in RDW TGK base, drive and gearbox tables")

    key = registration_scope_key(chosen)
    sanitized_children = {
        name: [
            {"record": row, "source_row_sha256": sha256_json(row),
             "applicability_precision": "exact_RDW_approval_variant_version_revision_scope"}
            for row in rows
        ]
        for name, rows in matched.items()
    }
    report = {
        "schema_version": 1,
        "probe_status": "schema_and_exact_scope_verified",
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_id": SOURCE_ID,
        "source_manifest_sha256": manifest_sha,
        "rights_status": manifest["rights"]["rights_status"],
        "license": "CC0 1.0",
        "market_scope": ["NL"],
        "approval_jurisdiction": "EU type approval",
        "metadata": metadata_reports,
        "sample_registration_observation": {
            "record": chosen,
            "source_row_sha256": sha256_json(chosen),
            "first_registration_date_is_model_year": False,
        },
        "approval_scope_key": key,
        "matched_official_tgk_rows": sanitized_children,
        "field_semantics": {
            "motorcode_is_confirmed_vag_factory_engine_code": False,
            "codetypeversnellingsbak_is_confirmed_vag_gearbox_code": False,
            "engine_gearbox_pair_claim": False,
            "model_year_inferred": False,
            "generation_inferred": False,
        },
        "applicability": {
            "exact_approval_variant_version_revision_scope": True,
            "individual_vehicle_fitment": False,
            "production_fitment": False,
            "ru_eaeu_applicability": False,
            "ecu_dtc_repair_applicability": False,
        },
        "source_snapshot_sha256": None,
        "source_snapshot_status": "probe_only_no_full_snapshot",
        "excluded_registration_fields": ["kenteken", "VIN", "holder", "ownership", "address", "personal data"],
        "pairing_policy": "Engine and gearbox rows are retained separately; no Cartesian product or engine/gearbox pair is created.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "rdw-vag-type-approval-probe.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    report["probe_report_sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/rdw-vag-probe"))
    args = parser.parse_args()
    report = probe(args.output_dir)
    print(json.dumps({
        "probe_status": report["probe_status"],
        "source_manifest_sha256": report["source_manifest_sha256"],
        "probe_report_sha256": report["probe_report_sha256"],
        "market_scope": report["market_scope"],
        "approval_scope_key": report["approval_scope_key"],
        "engine_rows": len(report["matched_official_tgk_rows"]["tgk_drive"]),
        "gearbox_rows": len(report["matched_official_tgk_rows"]["tgk_gearbox"]),
        "pair_claim": report["field_semantics"]["engine_gearbox_pair_claim"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
