#!/usr/bin/env python3
"""SQLite regression tests for technical-library rights, applicability and DTC namespace gates."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_FILES = (
    ROOT / "data/sql/vehicle-catalog.sql",
    ROOT / "data/sql/oem-dtc-index.sql",
    ROOT / "data/sql/dtc-catalog-links.sql",
    ROOT / "data/sql/technical-library.sql",
)
SCHEMA_PATH = ROOT / "data/schemas/technical-record-payloads.schema.json"
UTC = "2026-11-06T00:00:00Z"

class TechnicalLibrarySchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        for path in SQL_FILES:
            self.assertTrue(path.is_file(), f"missing SQL schema: {path}")
            self.db.executescript(path.read_text(encoding="utf-8"))
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    @staticmethod
    def h(char: str) -> str:
        return char * 64

    def insert_source_document(self, source_id: str, document_id: str, *, license_status: str = "open_license", redistribution_allowed: int = 1, source_sha256: str | None = None, market_scope: str = "EU") -> int:
        cur = self.db.execute(
            """INSERT INTO source_documents
               (source_id,publisher,document_id,document_type,revision,market_scope,
                source_url,source_sha256,license_status,license_name,reuse_scope,
                redistribution_allowed,retrieved_at_utc)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (source_id,"Synthetic test publisher",document_id,"other","r1",market_scope,
             f"https://example.invalid/{document_id}",source_sha256,license_status,
             "MIT" if license_status=="open_license" else None,"synthetic test fixture",
             redistribution_allowed,UTC),
        )
        return int(cur.lastrowid)

    def add_approved_technical_rights(self, source_document_id: int) -> None:
        self.db.execute(
            """INSERT INTO technical_source_rights
               (source_document_id,rights_status,commercial_use_allowed,display_allowed,
                offline_cache_allowed,bulk_reuse_allowed,redistribution_allowed,
                store_text_allowed,store_diagrams_allowed,store_structured_data_allowed,
                license_text_sha256,rights_revision,reviewed_at_utc)
               VALUES (?, 'approved',1,1,1,1,1,1,1,1,?,'r1',?)""",
            (source_document_id,self.h("c"),UTC),
        )

    def seed_published_exact_pair(self) -> tuple[int,int,int]:
        self.db.execute(
            """INSERT INTO vehicle_catalog_sources
               (source_id,publisher,source_title,source_url,source_version,market_scope,
                license_status,license_name,attribution_required,redistribution_allowed,
                reuse_scope,checked_at_utc)
               VALUES ('test-vag-source','Test publisher','Synthetic fixture',
                       'https://example.invalid/catalog','1','EU','cc0','CC0-1.0',
                       0,1,'test-only',?)""",(UTC,))
        self.db.execute(
            """INSERT INTO vehicle_catalog_source_rights
               (source_id,rights_status,commercial_use_allowed,display_allowed,offline_cache_allowed,
                bulk_reuse_allowed,redistribution_allowed,store_text_allowed,store_diagrams_allowed,
                store_structured_data_allowed,license_text_sha256,rights_revision,reviewed_at_utc)
               VALUES ('test-vag-source','approved',1,1,1,1,1,1,1,1,?,'r1',?)""",
            (self.h("c"),UTC),
        )
        self.db.execute("INSERT INTO vehicle_makes (make_key,display_name,group_name,status,created_at_utc) VALUES ('TEST_VW','Test Volkswagen','VOLKSWAGEN_GROUP','published',?)",(UTC,))
        make_id=self.db.execute("SELECT make_id FROM vehicle_makes WHERE make_key='TEST_VW'").fetchone()[0]
        self.db.execute("INSERT INTO vehicle_models (make_id,model_key,display_name,body_family,status) VALUES (?,'TEST_MODEL','Synthetic model',NULL,'published')",(make_id,))
        model_id=self.db.execute("SELECT model_id FROM vehicle_models WHERE model_key='TEST_MODEL'").fetchone()[0]
        self.db.execute("""INSERT INTO vehicle_generations
          (model_id,generation_key,type_code,platform_code,production_from,production_to,market_scope,notes,status)
          VALUES (?,'TEST_GEN','T1','TEST','2015','2016','EU',NULL,'published')""",(model_id,))
        generation_id=self.db.execute("SELECT generation_id FROM vehicle_generations WHERE generation_key='TEST_GEN'").fetchone()[0]
        self.db.execute("""INSERT INTO vehicle_variants
          (generation_id,variant_key,model_year_from,model_year_to,body_code,drive_configuration,fuel_type,emissions_variant,market_scope,status)
          VALUES (?,'TEST_VARIANT',2015,2016,NULL,'FWD','petrol',NULL,'EU','published')""",(generation_id,))
        variant_id=self.db.execute("SELECT variant_id FROM vehicle_variants WHERE variant_key='TEST_VARIANT'").fetchone()[0]
        self.db.execute("""INSERT INTO engine_codes
          (engine_code,manufacturer,engine_family,displacement_cc,fuel_type,aspiration,power_kw,power_hp,status)
          VALUES ('TESTE1','VOLKSWAGEN_GROUP',NULL,1600,'petrol','NA',100,136,'published')""")
        engine_id=self.db.execute("SELECT engine_id FROM engine_codes WHERE engine_code='TESTE1'").fetchone()[0]
        self.db.execute("""INSERT INTO transmission_codes
          (transmission_code,manufacturer,transmission_family,gear_count,transmission_type,drive_layout,status)
          VALUES ('TESTG1','VOLKSWAGEN_GROUP',NULL,6,'manual','FWD','published')""")
        transmission_id=self.db.execute("SELECT transmission_id FROM transmission_codes WHERE transmission_code='TESTG1'").fetchone()[0]
        self.db.execute("""INSERT INTO vehicle_catalog_evidence
          (source_id,document_id,document_revision,issue_date,retrieved_at_utc,evidence_locator,source_sha256,claim_type,review_status,reviewer_note)
          VALUES ('test-vag-source','TEST-PAIR','1',NULL,?,'https://example.invalid/test-pair',?,'engine_transmission_pair','candidate','synthetic fixture only')""",(UTC,self.h("a")))
        evidence_id=self.db.execute("SELECT evidence_id FROM vehicle_catalog_evidence WHERE document_id='TEST-PAIR'").fetchone()[0]
        self.db.execute("UPDATE vehicle_catalog_evidence SET review_status='publication_approved' WHERE evidence_id=?",(evidence_id,))
        self.db.execute("INSERT INTO powertrain_pair_evidence (variant_id,engine_id,transmission_id,evidence_id) VALUES (?,?,?,?)",(variant_id,engine_id,transmission_id,evidence_id))
        pair_id=self.db.execute("SELECT pair_id FROM powertrain_pair_evidence WHERE evidence_id=?",(evidence_id,)).fetchone()[0]
        source_document_id=self.insert_source_document("test-tech","TEST-TECH-1",source_sha256=self.h("b"),market_scope="EU")
        self.add_approved_technical_rights(source_document_id)
        self.db.execute("""INSERT INTO technical_documents
          (source_document_id,technical_kind,title,document_revision,market_scope,content_storage_mode,content_resource_key,content_sha256,review_status,created_at_utc)
          VALUES (?,'torque_specification','Synthetic torque record','r1','EU','structured_only','structured/torque.json',?,'candidate',?)""",(source_document_id,self.h("d"),UTC))
        technical_document_id=self.db.execute("SELECT technical_document_id FROM technical_documents WHERE title='Synthetic torque record'").fetchone()[0]
        self.db.execute("""INSERT INTO technical_applicability
          (vehicle_catalog_evidence_id,variant_id,engine_id,transmission_id,pair_evidence_id,market_scope,applicability_precision,evidence_locator,evidence_sha256,review_status)
          VALUES (?,?,?,?,?,'EU','engine_transmission_variant','https://example.invalid/test-pair',?,'candidate')""",
          (evidence_id,variant_id,engine_id,transmission_id,pair_id,self.h("a")))
        applicability_id=self.db.execute("SELECT applicability_id FROM technical_applicability WHERE pair_evidence_id=?",(pair_id,)).fetchone()[0]
        self.db.execute("INSERT INTO technical_document_applicability (technical_document_id,applicability_id,is_primary,note) VALUES (?,?,1,'synthetic test fixture')",(technical_document_id,applicability_id))
        self.db.execute("UPDATE technical_applicability SET review_status='publication_approved' WHERE applicability_id=?",(applicability_id,))
        self.db.execute("UPDATE technical_documents SET review_status='publication_approved' WHERE technical_document_id=?",(technical_document_id,))
        payload={"component":"Synthetic component","fastener":"M10 bolt","torque_value":42.0,"torque_unit":"Nm","angle_degrees":90,"condition":"synthetic test fixture only"}
        canonical=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
        record_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.db.execute("""INSERT INTO technical_records
          (technical_document_id,applicability_id,record_kind,record_revision,record_sha256,payload_json,review_status,created_at_utc)
          VALUES (?,?,'torque_specification','r1',?,?,'candidate',?)""",(technical_document_id,applicability_id,record_hash,canonical,UTC))
        record_id=self.db.execute("SELECT technical_record_id FROM technical_records WHERE technical_document_id=?",(technical_document_id,)).fetchone()[0]
        self.db.execute("UPDATE technical_records SET review_status='publication_approved' WHERE technical_record_id=?",(record_id,))
        self.db.commit()
        return source_document_id,technical_document_id,applicability_id

    def test_schema_defines_all_required_technical_sections(self) -> None:
        schema=json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        expected={"diagnostic_test_plan","repair_procedure","wiring_diagram","ecu_pinout","torque_specification","adaptation","service_interval","ecu_profile","oem_part","oem_supersession"}
        self.assertEqual(set(schema["$defs"])-{"step","connection","string_list"},expected)
        tables={r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"technical_source_rights","technical_documents","technical_applicability","technical_records"}<=tables)
        views={r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='view'")}
        self.assertTrue({"v_published_technical_records","v_generic_dtc_test_plans","v_vag_specific_dtc_test_plans"}<=views)

    def test_ecu_profile_and_oem_supersession_payload_contracts_are_explicit(self) -> None:
        schema=json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        ecu=schema["$defs"]["ecu_profile"]
        self.assertIn("anyOf",ecu)
        self.assertIn("ecu_family",ecu["properties"])
        supersession=schema["$defs"]["oem_supersession"]
        self.assertEqual(set(supersession["required"]),{"from_part_number","to_part_number","supersession_type"})
        self.assertIn("oem_supersession",schema["properties"]["record_kind"]["enum"])

    def test_exact_engine_transmission_record_requires_complete_evidence_and_publishes(self) -> None:
        self.seed_published_exact_pair()
        row=self.db.execute("""SELECT record_kind,document_revision,record_revision,market_scope,applicability_precision,
            engine_id,transmission_id,source_sha256,evidence_sha256,record_sha256,payload_json FROM v_published_technical_records""").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0],"torque_specification")
        self.assertEqual(row[3],"EU")
        self.assertEqual(row[4],"engine_transmission_variant")
        self.assertTrue(row[5] and row[6])
        self.assertEqual(len(row[7]),64)
        self.assertEqual(len(row[8]),64)
        self.assertEqual(hashlib.sha256(row[10].encode("utf-8")).hexdigest(),row[9])
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0],"ok")

    def test_generic_and_vag_specific_dtc_namespaces_cannot_be_mixed(self) -> None:
        source_document_id,_,applicability_id=self.seed_published_exact_pair()
        self.db.execute("""INSERT INTO oem_dtc_index
          (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,evidence_locator,applicability_level,
           vin_range_explicit,engine_code_explicit,transmission_code_explicit,ecu_hw_sw_explicit,review_status,source_claim_hash,created_at_utc)
          VALUES ('P0101','generic_sae_iso','UNKNOWN','UNKNOWN',?,'https://example.invalid/P0101','generic_only',0,0,0,0,'candidate',?,?)""",
          (source_document_id,self.h("f"),UTC))
        dtc_id=self.db.execute("SELECT oem_dtc_id FROM oem_dtc_index WHERE dtc_code='P0101'").fetchone()[0]
        self.db.execute("""INSERT INTO technical_documents
          (source_document_id,technical_kind,title,document_revision,market_scope,content_storage_mode,content_resource_key,content_sha256,review_status,created_at_utc)
          VALUES (?,'diagnostic_test_plan','Synthetic generic test plan','r1','EU','text','text/test-plan.json',?,'candidate',?)""",
          (source_document_id,self.h("d"),UTC))
        document_id=self.db.execute("SELECT technical_document_id FROM technical_documents WHERE title='Synthetic generic test plan'").fetchone()[0]
        self.db.execute("INSERT INTO technical_document_applicability (technical_document_id,applicability_id,is_primary) VALUES (?,?,0)",(document_id,applicability_id))
        with self.assertRaisesRegex(sqlite3.IntegrityError,"namespace"):
            self.db.execute("""INSERT INTO technical_records
              (technical_document_id,applicability_id,record_kind,record_revision,record_sha256,payload_json,dtc_namespace,oem_dtc_id,review_status,created_at_utc)
              VALUES (?,?,'diagnostic_test_plan','bad-namespace',?,'{}','manufacturer_specific_vag',?,'candidate',?)""",
              (document_id,applicability_id,self.h("e"),dtc_id,UTC))
        self.db.execute("""INSERT INTO technical_records
          (technical_document_id,applicability_id,record_kind,record_revision,record_sha256,payload_json,dtc_namespace,oem_dtc_id,review_status,created_at_utc)
          VALUES (?,?,'diagnostic_test_plan','generic-only',?,'{}','generic_sae_iso',?,'candidate',?)""",
          (document_id,applicability_id,self.h("e"),dtc_id,UTC))
        self.db.execute("UPDATE technical_documents SET review_status='publication_approved' WHERE technical_document_id=?",(document_id,))
        record_id=self.db.execute("SELECT technical_record_id FROM technical_records WHERE record_revision='generic-only'").fetchone()[0]
        self.db.execute("UPDATE technical_records SET review_status='publication_approved' WHERE technical_record_id=?",(record_id,))
        self.assertEqual(self.db.execute("SELECT count(*) FROM v_generic_dtc_test_plans").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM v_vag_specific_dtc_test_plans").fetchone()[0],0)
        self.db.execute("""INSERT INTO technical_records
          (technical_document_id,applicability_id,record_kind,record_revision,record_sha256,payload_json,dtc_namespace,review_status,created_at_utc)
          VALUES (?,?,'diagnostic_test_plan','unknown-namespace',?,'{}','unknown','candidate',?)""",
          (document_id,applicability_id,self.h("e"),UTC))
        unknown_id=self.db.execute("SELECT technical_record_id FROM technical_records WHERE record_revision='unknown-namespace'").fetchone()[0]
        with self.assertRaisesRegex(sqlite3.IntegrityError,"unknown DTC namespace"):
            self.db.execute("UPDATE technical_records SET review_status='publication_approved' WHERE technical_record_id=?",(unknown_id,))

    def test_permission_required_source_cannot_store_technical_content(self) -> None:
        source_document_id=self.insert_source_document("restricted-source","RESTRICTED-1",license_status="permission_required",redistribution_allowed=0,source_sha256=None)
        self.db.execute("INSERT INTO technical_source_rights (source_document_id,rights_status,rights_revision,reviewed_at_utc) VALUES (?,'permission_required','r1',?)",(source_document_id,UTC))
        self.db.execute("""INSERT INTO technical_documents
          (source_document_id,technical_kind,title,document_revision,market_scope,content_storage_mode,review_status,created_at_utc)
          VALUES (?,'repair_procedure','Restricted metadata only','r1','EU','reference_only','candidate',?)""",(source_document_id,UTC))
        document_id=self.db.execute("SELECT technical_document_id FROM technical_documents WHERE title='Restricted metadata only'").fetchone()[0]
        self.db.execute("""INSERT INTO technical_applicability
          (applicability_source_document_id,market_scope,applicability_precision,evidence_locator,evidence_sha256,review_status)
          VALUES (?,'EU','unknown','https://example.invalid/restricted',?,'candidate')""",(source_document_id,self.h("b")))
        applicability_id=self.db.execute("SELECT applicability_id FROM technical_applicability WHERE applicability_source_document_id=?",(source_document_id,)).fetchone()[0]
        self.db.execute("INSERT INTO technical_document_applicability (technical_document_id,applicability_id,is_primary) VALUES (?,?,1)",(document_id,applicability_id))
        with self.assertRaisesRegex(sqlite3.IntegrityError,"source rights"):
            self.db.execute("""INSERT INTO technical_records
              (technical_document_id,applicability_id,record_kind,record_revision,record_sha256,payload_json,created_at_utc)
              VALUES (?,?,'repair_procedure','r1',?,'{}',?)""",(document_id,applicability_id,self.h("c"),UTC))

    def test_model_year_only_applicability_cannot_be_published(self) -> None:
        source_document_id,_,_=self.seed_published_exact_pair()
        self.db.execute("""INSERT INTO technical_applicability
          (applicability_source_document_id,market_scope,model_year_from,model_year_to,applicability_precision,evidence_locator,evidence_sha256,review_status)
          VALUES (?,'EU',2015,2018,'model_year_only','https://example.invalid/model-years',?,'candidate')""",(source_document_id,self.h("a")))
        applicability_id=self.db.execute("SELECT applicability_id FROM technical_applicability WHERE applicability_precision='model_year_only'").fetchone()[0]
        with self.assertRaisesRegex(sqlite3.IntegrityError,"too broad"):
            self.db.execute("UPDATE technical_applicability SET review_status='publication_approved' WHERE applicability_id=?",(applicability_id,))

    def test_exact_powertrain_precision_requires_pair_evidence(self) -> None:
        source_document_id,_,_=self.seed_published_exact_pair()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("""INSERT INTO technical_applicability
              (applicability_source_document_id,market_scope,applicability_precision,evidence_locator,evidence_sha256,review_status)
              VALUES (?,'EU','engine_transmission_variant','https://example.invalid/no-pair',?,'candidate')""",(source_document_id,self.h("a")))

    def test_published_record_provenance_is_immutable(self) -> None:
        self.seed_published_exact_pair()
        with self.assertRaisesRegex(sqlite3.IntegrityError,"immutable"):
            self.db.execute("UPDATE technical_records SET payload_json='{}' WHERE review_status='publication_approved'")

    def test_foreign_key_integrity_is_clean(self) -> None:
        self.seed_published_exact_pair()
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(),[])


    def test_current_source_rights_revocation_hides_published_records(self) -> None:
        source_document_id, _, _ = self.seed_published_exact_pair()
        self.assertEqual(self.db.execute("SELECT count(*) FROM v_published_technical_records").fetchone()[0], 1)
        self.db.execute("UPDATE technical_source_rights SET rights_status='restricted' WHERE source_document_id=?", (source_document_id,))
        self.assertEqual(self.db.execute("SELECT count(*) FROM v_published_technical_records").fetchone()[0], 0)

    def test_vehicle_catalog_rights_are_required_for_exact_applicability(self) -> None:
        self.seed_published_exact_pair()
        self.db.execute("UPDATE vehicle_catalog_source_rights SET rights_status='restricted' WHERE source_id='test-vag-source'")
        evidence_id = self.db.execute("SELECT evidence_id FROM vehicle_catalog_evidence WHERE document_id='TEST-PAIR'").fetchone()[0]
        pair = self.db.execute("SELECT variant_id,engine_id,transmission_id,pair_id FROM powertrain_pair_evidence WHERE evidence_id=?", (evidence_id,)).fetchone()
        self.db.execute(
            """INSERT INTO technical_applicability
               (vehicle_catalog_evidence_id,variant_id,engine_id,transmission_id,pair_evidence_id,
                market_scope,applicability_precision,evidence_locator,evidence_sha256,review_status)
               VALUES (?,?,?,?,?,'EU','engine_transmission_variant','https://example.invalid/test-pair-recheck',?,'candidate')""",
            (evidence_id,pair[0],pair[1],pair[2],pair[3],self.h("a")),
        )
        applicability_id = self.db.execute("SELECT max(applicability_id) FROM technical_applicability").fetchone()[0]
        with self.assertRaisesRegex(sqlite3.IntegrityError, "offline reuse rights"):
            self.db.execute("UPDATE technical_applicability SET review_status='publication_approved' WHERE applicability_id=?", (applicability_id,))

    def test_permission_reference_is_required_when_approving_permission_granted_source(self) -> None:
        source_document_id = self.insert_source_document(
            "permission-source","PERMISSION-1",license_status="permission_granted",
            redistribution_allowed=1,source_sha256=self.h("b")
        )
        self.db.execute(
            """INSERT INTO technical_source_rights
               (source_document_id,rights_status,display_allowed,offline_cache_allowed,bulk_reuse_allowed,
                redistribution_allowed,store_text_allowed,store_diagrams_allowed,store_structured_data_allowed,
                license_text_sha256,rights_revision,reviewed_at_utc)
               VALUES (?,'not_reviewed',1,1,1,1,1,1,1,?,'r1',?)""",
            (source_document_id,self.h("c"),UTC),
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "permission reference"):
            self.db.execute("UPDATE technical_source_rights SET rights_status='approved' WHERE source_document_id=?", (source_document_id,))

if __name__ == "__main__":
    unittest.main()
