#!/usr/bin/env python3
"""Read-only probe for a pinned VehiclesDB release before changing the production lock.

The probe computes exact VAG make/model candidate and market-evidence counts
using the same rights/scope filters as the pack builder. It never creates a
SQLite output pack and never promotes candidates to repair fitment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from vag_identity_vehiclesdb_common import (
    EXCLUDED_COUNTRIES,
    _source_snapshot,
    _validate_inputs,
    _validate_source_file_pins,
    connect_readonly,
    expected_counts,
    read_json,
    table_names,
)


def probe_counts(
    lock_path: Path,
    source_db_path: Path,
    upstream_manifest_path: Path,
    attribution_path: Path,
    license_path: Path,
) -> dict[str, Any]:
    lock = read_json(lock_path)
    upstream = read_json(upstream_manifest_path)
    attribution_text = attribution_path.read_text(encoding="utf-8-sig")
    license_text = license_path.read_text(encoding="utf-8-sig")
    approved, excluded, scoped_makes, scoped_kinds = _validate_inputs(
        lock, upstream, attribution_text, license_text
    )
    snapshot = _source_snapshot(
        source_db_path, upstream_manifest_path, attribution_path, license_path
    )
    _validate_source_file_pins(lock, snapshot)

    source_db = connect_readonly(source_db_path)
    try:
        required_tables = {"makes", "models", "availability"}
        missing = required_tables - table_names(source_db)
        if missing:
            raise ValueError(f"VehiclesDB source SQLite is missing tables: {sorted(missing)}")

        upstream_sources = {
            str(item["id"]): item for item in upstream.get("sources", [])
        }
        allowed_placeholders = ",".join("?" for _ in approved)
        kind_placeholders = ",".join("?" for _ in scoped_kinds)
        make_placeholders = ",".join("?" for _ in scoped_makes)

        evidence_rows = list(source_db.execute(
            f"""SELECT a.kind,a.model_id,a.country,a.evidence,a.source
                FROM availability a
                WHERE a.source IN ({allowed_placeholders})
                  AND a.kind IN ({kind_placeholders})
                ORDER BY a.kind,a.model_id,a.country,a.source""",
            [*approved.keys(), *scoped_kinds],
        ))
        evidence_by_model: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in evidence_rows:
            item = dict(row)
            source = upstream_sources.get(item["source"])
            if source is None:
                raise ValueError(f"VehiclesDB evidence references an unknown source: {item['source']}")
            if item["country"] != source.get("country"):
                raise ValueError(f"VehiclesDB model evidence/source country mismatch: {item['source']}")
            if item["country"] in EXCLUDED_COUNTRIES:
                raise ValueError(f"Excluded market evidence entered probe: {item['country']}")
            evidence_by_model.setdefault((item["kind"], item["model_id"]), []).append(item)

        model_rows = list(source_db.execute(
            f"""SELECT m.kind,m.id,m.make_id
                FROM models m
                JOIN makes mk ON mk.kind=m.kind AND mk.id=m.make_id
                WHERE lower(m.make_id) IN ({make_placeholders})
                  AND lower(m.kind) IN ({kind_placeholders})
                ORDER BY lower(m.make_id),lower(m.id),m.kind,m.id""",
            [*scoped_makes, *scoped_kinds],
        ))
        selected = [
            row for row in model_rows
            if evidence_by_model.get((row["kind"], row["id"]))
        ]
        make_counts: dict[str, int] = {}
        selected_evidence = 0
        for row in selected:
            make_slug = str(row["make_id"]).lower()
            make_counts[make_slug] = make_counts.get(make_slug, 0) + 1
            selected_evidence += len(evidence_by_model[(row["kind"], row["id"])])
        countries = sorted({
            item["country"]
            for row in selected
            for item in evidence_by_model[(row["kind"], row["id"])]
        })
    finally:
        source_db.close()

    counts = {
        "sources": len(approved),
        "source_files": len(snapshot),
        "models": len(selected),
        "market_evidence": selected_evidence,
    }
    pinned = expected_counts(lock)
    return {
        "schema_version": 1,
        "status": "read_only_source_count_probe",
        "dataset_id": lock["dataset_id"],
        "publisher": lock["publisher"],
        "upstream_tag": lock["upstream_tag"],
        "dataset_version": upstream["version"],
        "data_license": lock["data_license"],
        "rights_status": "approved_by_published_license",
        "approved_source_license_map": approved,
        "excluded_source_reasons": excluded,
        "not_in_release_sources": lock["not_in_release_sources"],
        "market_scope_countries": countries,
        "applicability_precision": "make_model_name_only",
        "fitment_status": "not_established",
        "fitment_claim": False,
        "exact_fitment": False,
        "identity_only_use": lock["build_policy"]["identity_only_use"],
        "safety_critical_reliance": lock["build_policy"]["safety_critical_reliance"],
        "repair_decision_use": lock["build_policy"]["repair_decision_use"],
        "open_data_policy_notice": lock["build_policy"]["open_data_policy_notice"],
        "ru_evidence_present": False,
        "engine_codes_included": False,
        "gearbox_codes_included": False,
        "ecu_fitment_included": False,
        "counts": counts,
        "pinned_counts": pinned,
        "counts_match": counts == pinned,
        "make_counts": dict(sorted(make_counts.items())),
        "source_snapshot": {
            name: {"byte_size": item["byte_size"], "sha256": item["sha256"]}
            for name, item in sorted(snapshot.items())
        },
        "no_pack_written": True,
        "no_production_import": True,
        "warning": (
            "Identity and foreign-market presence candidates only. This probe does not "
            "establish RU/EAEU applicability, generation, model year, engine/gearbox codes, "
            "ECU fitment or repair applicability."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--attribution", type=Path, required=True)
    parser.add_argument("--license", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-count-match", action="store_true")
    args = parser.parse_args(argv)
    report = probe_counts(
        args.lock, args.source_db, args.manifest, args.attribution, args.license
    )
    if args.require_count_match and not report["counts_match"]:
        raise SystemExit("VehiclesDB probe counts differ from the pinned lock.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
