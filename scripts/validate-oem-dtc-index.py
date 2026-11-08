#!/usr/bin/env python3
"""Validate the evidence-first OEM DTC index contract without external packages."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data/schemas/oem-dtc-index.schema.json"
SQL_PATH = ROOT / "data/sql/oem-dtc-index.sql"
GENERIC_DTC_PATTERN = re.compile(r"^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|P34[0-9A-F]{2}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3})$")
MANUFACTURER_DTC_PATTERN = re.compile(r"^(?:P1[0-9A-F]{3}|P3[0-3][0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$")


def expect_integrity_error(fn, expected: str) -> None:
    try:
        fn()
    except sqlite3.IntegrityError as exc:
        if expected not in str(exc):
            raise AssertionError(f"Expected error containing {expected!r}; got {exc}") from exc
        return
    raise AssertionError(f"Expected SQLite IntegrityError containing {expected!r}")


def main() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    required = set(schema["required"])
    if not {"record_id", "dtc", "dtc_namespace", "manufacturer", "market_scope",
            "source_document", "applicability", "ecu", "provenance", "rights", "review"}.issubset(required):
        raise AssertionError("OEM DTC JSON schema is missing mandatory evidence fields")
    props = schema["properties"]
    namespace_rules = schema.get("allOf", [])
    if len(namespace_rules) != 3:
        raise AssertionError("DTC JSON schema must bind generic, VAG-specific and other-OEM namespaces to manufacturer identity")
    patterns = {rule["if"]["properties"]["dtc_namespace"]["const"]: rule["then"]["properties"]["dtc"]["pattern"] for rule in namespace_rules}
    if patterns.get("generic_sae_iso") != GENERIC_DTC_PATTERN.pattern or patterns.get("manufacturer_specific_vag") != MANUFACTURER_DTC_PATTERN.pattern or patterns.get("manufacturer_specific_other") != MANUFACTURER_DTC_PATTERN.pattern:
        raise AssertionError("DTC JSON schema namespace code-range patterns are inconsistent")
    for code in ("P0001","P2ABC","P34C8","B0ABC","C0ABC","U0ABC"):
        if not GENERIC_DTC_PATTERN.fullmatch(code): raise AssertionError(f"Generic boundary code rejected: {code}")
    for code in ("P1ABC","P30AB","P33AB","B1ABC","B2ABC","C1ABC","C2ABC","U1ABC","U2ABC"):
        if not MANUFACTURER_DTC_PATTERN.fullmatch(code): raise AssertionError(f"Manufacturer boundary code rejected: {code}")
    for code in ("P1A00","P3000","B1ABC","C2ABC","U1ABC"):
        if GENERIC_DTC_PATTERN.fullmatch(code): raise AssertionError(f"Manufacturer code accepted as generic: {code}")
    for code in ("P0300","P2ABC","P34C8","B0ABC","C0ABC","U0ABC","U3ABC"):
        if MANUFACTURER_DTC_PATTERN.fullmatch(code): raise AssertionError(f"Generic code accepted as manufacturer-specific: {code}")
    for code in ("U3ABC","P35AB","P39AB","B3ABC","C3ABC"):
        if GENERIC_DTC_PATTERN.fullmatch(code) or MANUFACTURER_DTC_PATTERN.fullmatch(code):
            raise AssertionError(f"Unresolved or reserved range was admitted: {code}")
    for name in ("ecu", "source_document", "applicability", "provenance", "rights", "review"):
        if name not in props:
            raise AssertionError(f"Missing JSON schema property: {name}")

    sql = SQL_PATH.read_text(encoding="utf-8")
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(sql)

    tables = {row[0] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    expected_tables = {
        "source_documents", "ecu_identities", "oem_dtc_index",
        "repair_procedure_references"
    }
    if not expected_tables.issubset(tables):
        raise AssertionError(f"Missing SQL tables: {expected_tables - tables}")
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise AssertionError("SQLite integrity_check failed")

    db.execute("""INSERT INTO source_documents
      (source_id,publisher,document_id,document_type,revision,market_scope,
       license_status,reuse_scope,redistribution_allowed,retrieved_at_utc)
      VALUES ('OBDex','OBDex','snapshot','dtc_table','1','UNKNOWN',
              'cc0','generic research only',1,'2026-11-03T00:00:00Z')""")
    cc0_source = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    expect_integrity_error(
        lambda: db.execute("""INSERT INTO oem_dtc_index
          (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,
           evidence_locator,applicability_level,source_claim_hash,created_at_utc)
          VALUES ('P0123','generic_sae_iso','VOLKSWAGEN','RU',?,
                  'row 1','generic_only',?,'2026-11-03T00:00:00Z')""",
          (cc0_source, "a" * 64)),
        "generic SAE/ISO DTC must use UNKNOWN manufacturer"
    )

    # A generic record is valid only with an unknown manufacturer, and this
    # invariant must also survive later updates.
    db.execute("""INSERT INTO oem_dtc_index
      (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,
       evidence_locator,applicability_level,source_claim_hash,created_at_utc)
      VALUES ('P0124','generic_sae_iso','UNKNOWN','UNKNOWN',?,
              'generic reference','generic_only',?,'2026-11-03T00:00:00Z')""",
      (cc0_source, "d" * 64))
    generic_record = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    expect_integrity_error(
        lambda: db.execute("UPDATE oem_dtc_index SET manufacturer='AUDI' WHERE oem_dtc_id=?", (generic_record,)),
        "generic SAE/ISO DTC must use UNKNOWN manufacturer"
    )
    expect_integrity_error(
        lambda: db.execute("""INSERT INTO oem_dtc_index
          (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,evidence_locator,applicability_level,source_claim_hash,created_at_utc)
          VALUES ('P1125','generic_sae_iso','UNKNOWN','UNKNOWN',?,'wrong generic range','generic_only',?,'2026-11-03T00:00:00Z')""",
          (cc0_source, "1" * 64)),
        "generic SAE/ISO DTC code is outside allowed generic OBD-II ranges"
    )
    expect_integrity_error(lambda: db.execute("UPDATE oem_dtc_index SET dtc_code='P1125' WHERE oem_dtc_id=?", (generic_record,)),
        "generic SAE/ISO DTC code is outside allowed generic OBD-II ranges")
    expect_integrity_error(lambda: db.execute("INSERT INTO oem_dtc_index (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,evidence_locator,applicability_level,source_claim_hash,created_at_utc) VALUES ('U3ABC','generic_sae_iso','UNKNOWN','UNKNOWN',?,'unresolved U3 range','generic_only',?,'2026-11-03T00:00:00Z')",(cc0_source,"f"*64)), "generic SAE/ISO DTC code is outside allowed generic OBD-II ranges")

    # A VAG-specific namespace must name an actual VAG Group make.
    expect_integrity_error(
        lambda: db.execute("""INSERT INTO oem_dtc_index
          (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,
           evidence_locator,applicability_level,source_claim_hash,created_at_utc)
          VALUES ('P1125','manufacturer_specific_vag','UNKNOWN','RU',?,
                  'row 2','unknown',?,'2026-11-03T00:00:00Z')""",
          (cc0_source, "e" * 64)),
        "VAG-specific DTC requires a VAG Group manufacturer"
    )

    db.execute("""INSERT INTO source_documents
      (source_id,publisher,document_id,document_type,revision,market_scope,
       license_status,reuse_scope,redistribution_allowed,retrieved_at_utc)
      VALUES ('synthetic-vag-test','Synthetic VAG test source','vag-dtc-test','dtc_table','r1','RU',
              'permission_granted','synthetic fixture only',1,'2026-11-03T00:00:00Z')""")
    vag_source = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    expect_integrity_error(lambda: db.execute("""INSERT INTO oem_dtc_index
      (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,evidence_locator,applicability_level,source_claim_hash,created_at_utc)
      VALUES ('P2345','manufacturer_specific_vag','AUDI','RU',?,'generic P2 range','exact_ecu_hw_sw',?,'2026-11-03T00:00:00Z')""",(vag_source,"2"*64)),
      "manufacturer-controlled DTC code is outside allowed OBD-II ranges")
    expect_integrity_error(lambda: db.execute("""INSERT INTO oem_dtc_index
      (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,evidence_locator,applicability_level,source_claim_hash,created_at_utc)
      VALUES ('P34C8','manufacturer_specific_vag','AUDI','RU',?,'generic P34 range','exact_ecu_hw_sw',?,'2026-11-03T00:00:00Z')""",(vag_source,"3"*64)),
      "manufacturer-controlled DTC code is outside allowed OBD-II ranges")
    for reserved_code in ("P35A6", "P39A6", "U3ABC"):
        expect_integrity_error(lambda code=reserved_code: db.execute("""INSERT INTO oem_dtc_index
          (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,evidence_locator,applicability_level,source_claim_hash,created_at_utc)
          VALUES (?,'manufacturer_specific_vag','AUDI','RU',?,'unresolved or reserved range','exact_ecu_hw_sw',?,'2026-11-03T00:00:00Z')""",(code,vag_source,"4"*64)),
          "manufacturer-controlled DTC code is outside allowed OBD-II ranges")
    db.execute("""INSERT INTO source_documents
      (source_id,publisher,document_id,document_type,revision,market_scope,
       license_status,reuse_scope,redistribution_allowed,retrieved_at_utc)
      VALUES ('OEM','OEM','restricted-doc','dtc_table','A','RU',
              'permission_required','view only',0,'2026-11-03T00:00:00Z')""")
    restricted_source = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("""INSERT INTO oem_dtc_index
      (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,
       evidence_locator,applicability_level,source_claim_hash,created_at_utc)
      VALUES ('P1125','manufacturer_specific_vag','AUDI','RU',?,
              'page 4, table 2','exact_ecu_hw_sw',?,'2026-11-03T00:00:00Z')""",
      (restricted_source, "b" * 64))
    restricted_record = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    expect_integrity_error(
        lambda: db.execute(
            "UPDATE oem_dtc_index SET review_status='publication_approved' WHERE oem_dtc_id=?",
            (restricted_record,)
        ),
        "source reuse rights not cleared"
    )

    db.execute("""INSERT INTO oem_dtc_index
      (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,
       evidence_locator,applicability_level,source_claim_hash,created_at_utc)
      VALUES ('P33A6','manufacturer_specific_vag','VOLKSWAGEN','RU',?,
              'page 9, ECU table','exact_ecu_hw_sw',?,'2026-11-03T00:00:00Z')""",
      (vag_source, "c" * 64))
    publishable_record = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute(
        "UPDATE oem_dtc_index SET review_status='publication_approved' WHERE oem_dtc_id=?",
        (publishable_record,)
    )

    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise AssertionError("Foreign key violations detected")
    print("OEM DTC index validation passed: canonical DTC shape, disjoint generic/manufacturer ranges, namespace/manufacturer and rights gates.")


if __name__ == "__main__":
    main()
