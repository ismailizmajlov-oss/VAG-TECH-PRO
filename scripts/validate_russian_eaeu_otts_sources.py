#!/usr/bin/env python3
"""Fail-closed validation for the Russian/EAEU OTTS reuse-rights register.

This validates source permission metadata only. It does not fetch, scrape, or import
any OTTS record or PDF.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "russian-eaeu-otts-sources.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
AFFIRMATIVE = {
    "allowed", "permitted", "yes", "true", "granted", "approved",
    "cc0", "public_domain", "open_license", "permission_granted",
}
BLOCKED_STATES = {"permission_required", "restricted_for_product_distribution", "discovery_only"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> dict[str, Any]:
    policy = data.get("ingestion_policy")
    require(isinstance(policy, dict), "ingestion_policy must be an object")
    for key in (
        "require_commercial_use_rights",
        "require_display_rights",
        "require_offline_cache_rights",
        "require_bulk_reuse_rights",
        "require_pdf_redistribution_rights_if_pdfs_are_packaged",
        "no_scraping_or_undocumented_endpoints",
        "no_import_until_all_required_rights_are_confirmed",
    ):
        require(policy.get(key) is True, f"ingestion policy must keep {key}=true")

    sources = data.get("sources")
    require(isinstance(sources, list) and sources, "sources must be a non-empty array")
    ids: set[str] = set()
    counts: dict[str, int] = {}
    for source in sources:
        require(isinstance(source, dict), "each source must be an object")
        source_id = source.get("source_id")
        require(isinstance(source_id, str) and source_id.strip(), "source_id is required")
        require(source_id not in ids, f"duplicate source_id: {source_id}")
        ids.add(source_id)

        status = source.get("status")
        require(isinstance(status, str) and status, f"{source_id}: status is required")
        counts[status] = counts.get(status, 0) + 1
        ingested = source.get("data_ingested")
        require(isinstance(ingested, bool), f"{source_id}: data_ingested must be boolean")
        license_data = source.get("license")
        require(isinstance(license_data, dict), f"{source_id}: license metadata is required")

        snapshot_hash = source.get("source_snapshot_sha256")
        if ingested:
            require(status not in BLOCKED_STATES, f"{source_id}: blocked source cannot be ingested")
            require(isinstance(snapshot_hash, str) and SHA256_RE.fullmatch(snapshot_hash) is not None,
                    f"{source_id}: imported source requires a verified 64-character SHA-256")
            require(bool(license_data.get("identifier")), f"{source_id}: imported source requires a license identifier")
            for field in ("commercial_use", "display", "offline_cache", "bulk_export"):
                value = license_data.get(field)
                require(isinstance(value, str) and value.strip(), f"{source_id}: missing license.{field}")
                require(value.lower() in AFFIRMATIVE,
                        f"{source_id}: license.{field} is not an explicit affirmative permission")
            require(bool(source.get("market_scope")), f"{source_id}: imported source requires market_scope")
            require(bool(source.get("applicability_precision")),
                    f"{source_id}: imported source requires applicability_precision")
            require(bool(source.get("source_revision") or source.get("revision") or source.get("upstream_revision")),
                    f"{source_id}: imported source requires a source revision")
        else:
            require(snapshot_hash is None, f"{source_id}: non-ingested source must not claim a snapshot hash")
            require(status in BLOCKED_STATES or status in {"approved_by_published_license", "research_only"},
                    f"{source_id}: non-ingested source has an unsupported status")

        if source_id in {"hpt-su-otts-api", "otts-bot-and-public-aggregators", "otts-baza-autoregistr"}:
            require(status == "restricted_for_product_distribution",
                    f"{source_id}: aggregator must remain restricted for product distribution")
            require(ingested is False, f"{source_id}: restricted aggregator must not be imported")

    expected = {
        "rosstandart-fgis-reestr-kts": ("permission_required", False),
        "eaeu-open-data-portal": ("discovery_only", False),
        "hpt-su-otts-api": ("restricted_for_product_distribution", False),
        "otts-bot-and-public-aggregators": ("restricted_for_product_distribution", False),
        "otts-baza-autoregistr": ("restricted_for_product_distribution", False),
    }
    by_id = {item["source_id"]: item for item in sources}
    for source_id, (expected_status, expected_ingested) in expected.items():
        require(source_id in by_id, f"required source entry missing: {source_id}")
        item = by_id[source_id]
        require(item.get("status") == expected_status, f"{source_id}: unexpected status")
        require(item.get("data_ingested") is expected_ingested, f"{source_id}: unexpected ingestion state")

    bot = by_id["otts-bot-and-public-aggregators"]["license"]
    require(bot.get("pdf_redistribution") == "prohibited", "OTTS.BOT PDF redistribution boundary missing")
    require(bot.get("bulk_export") == "automated_scraping_and_mass_requests_prohibited",
            "OTTS.BOT scraping boundary missing")

    autoreg = by_id["otts-baza-autoregistr"]["license"]
    require(autoreg.get("bulk_export") ==
            "systematic_extraction_of_substantial_database_part_for_publication_resale_or_competing_catalog_prohibited",
            "АВТОРЕГИСТР substantial-extraction boundary missing")

    return {
        "status": "validated_fail_closed",
        "source_count": len(sources),
        "status_counts": dict(sorted(counts.items())),
        "ingested_count": sum(1 for item in sources if item.get("data_ingested") is True),
        "blocked_aggregators": 3,
    }


def main() -> int:
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("source register root must be an object")
    result = validate(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"OTTS source-rights validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
