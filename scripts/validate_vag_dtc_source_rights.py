#!/usr/bin/env python3
"""Fail-closed validation of VAG-specific DTC source permissions."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
AFFIRMATIVE = {"allowed", "permitted", "yes", "true", "granted", "approved", "cc0", "open_license"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> dict[str, Any]:
    policy = data.get("policy")
    require(isinstance(policy, dict), "policy must be an object")
    for key in (
        "generic_obd_is_not_vag_specific",
        "model_year_match_is_not_exact_fitment",
        "vin_fitment_requires_primary_evidence",
        "oem_documents_may_not_be_redistributed_without_permission",
        "manufacturer_data_requires_rights_review_before_storage_or_publication",
    ):
        require(policy.get(key) is True, f"policy must keep {key}=true")

    sources = data.get("sources")
    require(isinstance(sources, list) and sources, "sources must be a non-empty array")
    by_id: dict[str, dict[str, Any]] = {}
    for source in sources:
        require(isinstance(source, dict), "each source must be an object")
        source_id = source.get("source_id")
        require(isinstance(source_id, str) and source_id.strip(), "source_id is required")
        require(source_id not in by_id, f"duplicate source_id: {source_id}")
        by_id[source_id] = source

        if source.get("data_ingested") is True:
            rights = source.get("rights")
            require(isinstance(rights, dict), f"{source_id}: rights object required for ingestion")
            require(bool(source.get("source_snapshot_sha256")) and
                    SHA256_RE.fullmatch(str(source["source_snapshot_sha256"])) is not None,
                    f"{source_id}: imported data requires source SHA-256")
            require(bool(source.get("market_scope")), f"{source_id}: imported data requires market scope")
            require(source.get("verification_status") in {"verified", "publication_approved"},
                    f"{source_id}: imported data must have an approved verification status")
            for key in ("commercial_use", "display", "offline_cache", "bulk_export"):
                value = rights.get(key)
                require(isinstance(value, str) and value.lower() in AFFIRMATIVE,
                        f"{source_id}: rights.{key} is not explicitly permitted")
            require(rights.get("redistribution_allowed") is not False,
                    f"{source_id}: redistribution is explicitly denied")

        decision = str(source.get("project_decision", "")).lower()
        if any(term in decision for term in ("do_not_import", "do not import", "quarantine_only", "blocked")):
            require(source.get("data_ingested", False) is False,
                    f"{source_id}: blocked/quarantined source cannot be ingested")

    openvag = by_id.get("riz4d-openvag-dtc-quarantine")
    require(openvag is not None, "OpenVAG quarantine entry is required")
    require(openvag.get("data_ingested") is False, "OpenVAG must remain non-ingested")
    require(openvag.get("source_snapshot_sha256") is None, "OpenVAG must not claim a data snapshot hash")
    require(openvag.get("applicability_precision") == "none", "OpenVAG applicability must remain none")
    require(openvag.get("verification_status") == "quarantine_only", "OpenVAG must remain quarantined")
    require("UNKNOWN" in openvag.get("market_scope", []), "OpenVAG market scope must remain UNKNOWN")

    snapshot = openvag.get("snapshot_check")
    require(isinstance(snapshot, dict), "OpenVAG snapshot evidence is required")
    require(snapshot.get("database_blob_count") == 0, "OpenVAG database blob count must remain zero")
    require(snapshot.get("release_count") == 0, "OpenVAG release count must remain zero")
    require(snapshot.get("data_snapshot_available") is False, "OpenVAG data snapshot must remain unavailable")
    rights = openvag.get("rights")
    require(isinstance(rights, dict), "OpenVAG rights metadata is required")
    require(rights.get("database_data_license") == "not_separately_established",
            "OpenVAG database data license must not be inferred from the MIT code license")

    return {
        "status": "validated_fail_closed",
        "source_count": len(sources),
        "ingested_count": sum(1 for source in sources if source.get("data_ingested") is True),
        "openvag": "quarantine_only_no_data_snapshot",
    }


def main() -> int:
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "source register root must be an object")
    print(json.dumps(validate(data), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"VAG DTC source-rights validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
