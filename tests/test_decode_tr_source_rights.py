#!/usr/bin/env python3
"""Rights and quarantine gate for the independent decode.tr VAG code catalogue."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data/source-manifests/vag-factory-source-register.json"
SOURCE_ID = "decode-tr-vag-engine-transmission-catalog"


def main() -> None:
    manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
    matches = [item for item in manifest["sources"] if item.get("source_id") == SOURCE_ID]
    if len(matches) != 1:
        raise SystemExit(f"Expected one {SOURCE_ID} entry; found {len(matches)}")
    source = matches[0]
    rights = source.get("rights", {})
    applicability = source.get("applicability", {})

    required_false = (
        source.get("product_import_allowed") is False,
        source.get("data_ingested") is False,
        source.get("source_snapshot_sha256") is None,
        source.get("hash_status") == "not_downloaded_no_ingestion",
        rights.get("permission_status") == "not_obtained",
        rights.get("automated_extraction_allowed") == "not_authorized",
        rights.get("bulk_export_allowed") == "not_established",
        rights.get("offline_cache_allowed") == "not_established",
        rights.get("commercial_display_allowed") == "not_established",
        rights.get("redistribution_allowed") == "not_established",
        applicability.get("market_scope") == "UNKNOWN",
        applicability.get("exact_engine_code_fitment") is False,
        applicability.get("exact_gearbox_code_fitment") is False,
        applicability.get("engine_gearbox_pairing") is False,
        applicability.get("russian_market_scope") is False,
        applicability.get("eaeu_market_scope") is False,
    )
    if not all(required_false):
        raise SystemExit("decode.tr candidate crossed an import, rights, market or fitment boundary")

    if "2015" not in source.get("source_revision", ""):
        raise SystemExit("decode.tr source revision must preserve the publisher's 2015 ETKA extract disclosure")
    if "not an open" not in rights.get("publisher_rights_statement", "").lower():
        raise SystemExit("decode.tr publisher's no-open-licence statement is missing")
    reviewed_urls = {item.get("url") for item in source.get("evidence_reviewed", [])}
    if not {"https://decode.tr/motor-kodu-cozucu", "https://decode.tr/hakkinda"}.issubset(reviewed_urls):
        raise SystemExit("decode.tr lookup and publisher-rights evidence must both be retained")

    print("decode.tr source-rights gate passed: quarantined, not ingested, no market or powertrain-pair claim.")


if __name__ == "__main__":
    main()
