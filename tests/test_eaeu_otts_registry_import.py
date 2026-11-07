from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import import_eaeu_otts_registry_export as importer  # noqa: E402

NS = importer.EXPECTED_NAMESPACE


def _xml(*, ambiguous: bool = False, include_sbkts: bool = True) -> bytes:
    second_variant = ""
    if ambiguous:
        second_variant = """
        <VehicleVariantDetails>
          <VehicleTypeVariantId>VAR-AMBIGUOUS</VehicleTypeVariantId>
          <EngineDetails><VehicleComponentMakeName>Test Engine A</VehicleComponentMakeName><VehicleComponentModelCode>TEST-ENG-A</VehicleComponentModelCode></EngineDetails>
          <EngineDetails><VehicleComponentMakeName>Test Engine B</VehicleComponentMakeName><VehicleComponentModelCode>TEST-ENG-B</VehicleComponentModelCode></EngineDetails>
          <VehicleTransmissionDetails>
            <TransmissionUnitDetails><VehicleUnitKindCode>05</VehicleUnitKindCode><VehicleComponentModelCode>TEST-GEAR-A</VehicleComponentModelCode></TransmissionUnitDetails>
            <TransmissionUnitDetails><VehicleUnitKindCode>05</VehicleUnitKindCode><VehicleComponentModelCode>TEST-GEAR-B</VehicleComponentModelCode></TransmissionUnitDetails>
          </VehicleTransmissionDetails>
        </VehicleVariantDetails>
        """
    sbkts = ""
    if include_sbkts:
        sbkts = """
        <VehicleConformityDocDetails>
          <UnifiedCountryCode>RU</UnifiedCountryCode>
          <DocId>SBKTS-SYNTHETIC-01</DocId>
          <DocStartDate>2025-02-01</DocStartDate>
          <ConformityDocKindCode>40</ConformityDocKindCode>
          <ApplicantDetails><BusinessEntityName>Applicant Secret Synthetic</BusinessEntityName></ApplicantDetails>
          <VehicleV2Details><VehicleIdentificationNumberId>VIN-SYNTHETIC-DO-NOT-STORE</VehicleIdentificationNumberId></VehicleV2Details>
        </VehicleConformityDocDetails>
        """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <ConformityVehicleDocsRegistryDetails xmlns="{NS}">
      <EDocHeader>
        <EDocCode>R.TR.TS.07.001</EDocCode>
        <EDocDateTime>2026-11-06T00:00:00Z</EDocDateTime>
        <LanguageCode>ru</LanguageCode>
      </EDocHeader>
      <VehicleConformityDocDetails>
        <UnifiedCountryCode>RU</UnifiedCountryCode>
        <DocId>OTTS-SYNTHETIC-01</DocId>
        <DocCreationDate>2025-01-01</DocCreationDate>
        <DocStartDate>2025-01-02</DocStartDate>
        <DocValidityDate>2030-01-01</DocValidityDate>
        <ConformityDocKindCode>30</ConformityDocKindCode>
        <ConformityAuthorityInformationDetails><BusinessEntityName>Test Certification Authority</BusinessEntityName></ConformityAuthorityInformationDetails>
        <VehicleTypeDetails>
          <VehicleMakeName>Volkswagen</VehicleMakeName>
          <VehicleMakeCode>VW</VehicleMakeCode>
          <VehicleCommercialName>Test Model</VehicleCommercialName>
          <VehicleTypeId>TYPE-TEST-01</VehicleTypeId>
          <VehicleTechCategoryCode>M1</VehicleTechCategoryCode>
        </VehicleTypeDetails>
        <VehicleManufacturerDetails><BusinessEntityName>Test Vehicle Manufacturer</BusinessEntityName></VehicleManufacturerDetails>
        <ConformityDocStatusDetails><DocStatusCode>1</DocStatusCode></ConformityDocStatusDetails>
        <VehicleVariantDetails>
          <VehicleTypeVariantId>VAR-EXACT-01</VehicleTypeVariantId>
          <VehicleEcoClassCode>06</VehicleEcoClassCode>
          <EngineDetails>
            <VehicleComponentMakeName>Test Engine Make</VehicleComponentMakeName>
            <VehicleComponentModelCode>TEST-ENGINE-CODE-01</VehicleComponentModelCode>
            <VehicleComponentText>synthetic test engine</VehicleComponentText>
            <EngineCylinderQuantity>4</EngineCylinderQuantity>
            <EngineCapacityMeasure measurementUnitCode="CMQ">1395</EngineCapacityMeasure>
            <EngineMaxPowerDetails><EngineMaxPowerMeasure measurementUnitCode="KWT">110</EngineMaxPowerMeasure></EngineMaxPowerDetails>
            <EngineMaxTorqueDetails><EngineMaxTorqueMeasure measurementUnitCode="NEW">250</EngineMaxTorqueMeasure></EngineMaxTorqueDetails>
          </EngineDetails>
          <VehicleTransmissionDetails>
            <TransmissionUnitDetails>
              <VehicleUnitKindCode>05</VehicleUnitKindCode>
              <VehicleComponentMakeName>Test Gearbox Make</VehicleComponentMakeName>
              <VehicleComponentModelCode>TEST-GEARBOX-CODE-01</VehicleComponentModelCode>
              <VehicleComponentText>synthetic test gearbox</VehicleComponentText>
              <TransmissionUnitGearQuantity>6</TransmissionUnitGearQuantity>
            </TransmissionUnitDetails>
            <TransmissionUnitDetails>
              <VehicleUnitKindCode>10</VehicleUnitKindCode>
              <VehicleComponentModelCode>TEST-TRANSFER-CASE-01</VehicleComponentModelCode>
            </TransmissionUnitDetails>
          </VehicleTransmissionDetails>
          <ECUModelCode>TEST-ECU-MODEL-01</ECUModelCode>
        </VehicleVariantDetails>
        {second_variant}
      </VehicleConformityDocDetails>
      {sbkts}
    </ConformityVehicleDocsRegistryDetails>
    """.encode("utf-8")


def _source_manifest(rights: dict | None = None) -> dict:
    return {
        "updated_at": "2026-11-06",
        "sources": [{
            "source_id": importer.SOURCE_ID,
            "url": "https://portal.eaeunion.org/",
            "source_revision": "Decision 88 / R.TR.TS.07.001 v1.0.0",
            "market_scope": ["EAEU"],
            "rights": rights or {
                "permission_status": "not_obtained",
                "review_status": "not_approved",
                "commercial_use_allowed": "not_established",
                "bulk_reuse_allowed": "not_established",
                "offline_cache_allowed": "not_established",
                "display_and_redistribution_allowed": "not_established",
                "permission_evidence": None,
            },
        }],
    }


class EaeuOttsRegistryImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.xml_path = self.root / "registry.xml"
        self.xml_path.write_bytes(_xml(ambiguous=True))
        self.manifest_path = self.root / "source-register.json"
        self.manifest_path.write_text(json.dumps(_source_manifest(), ensure_ascii=False), encoding="utf-8")
        self.retrieved_at = "2026-11-06T07:19:20+07:00"

    def tearDown(self):
        self.temp.cleanup()

    def test_schema_and_variant_scoped_candidates_are_parsed(self):
        parsed = importer.parse_registry_export(self.xml_path.read_bytes())
        self.assertEqual(parsed["schema_id"], "R.TR.TS.07.001")
        self.assertEqual(parsed["schema_version"], "1.0.0")
        self.assertEqual(parsed["counts"]["documents"], 1)
        self.assertEqual(parsed["counts"]["variants"], 2)
        self.assertEqual(parsed["counts"]["engine_candidates"], 3)
        self.assertEqual(parsed["counts"]["transmission_unit_candidates"], 4)
        self.assertEqual(parsed["counts"]["ecu_candidates"], 1)
        self.assertEqual(parsed["counts"]["same_variant_pair_candidates"], 1)
        exact = parsed["documents"][0]["variants"][0]
        self.assertEqual(exact["engines"][0]["component_model_code"], "TEST-ENGINE-CODE-01")
        self.assertEqual(exact["transmissions"][0]["unit_kind_code"], "05")
        self.assertEqual(exact["transmissions"][0]["unit_kind_label"], "gearbox")
        self.assertEqual(exact["pair_candidates"][0]["verification_status"], "candidate_unverified")
        self.assertEqual(exact["pair_candidates"][0]["applicability_precision"], "same_approval_variant_id_single_pair_candidate")
        self.assertEqual(exact["pair_candidates"][0]["evidence_rule"], "single_engine_and_single_gearbox_code_nested_under_same_approval_variant_element")
        self.assertEqual(exact["engines"][0]["code_namespace"], "EAEU_TR_TS_018_2011_VehicleComponentModelCode_engine")
        ambiguous = parsed["documents"][0]["variants"][1]
        self.assertEqual(ambiguous["pair_candidates"], [])

    def test_multiple_variants_require_variant_ids_under_decision_88_rule_34(self):
        raw = _xml(ambiguous=True, include_sbkts=False).replace(
            b"<VehicleTypeVariantId>VAR-AMBIGUOUS</VehicleTypeVariantId>", b"", 1
        )
        with self.assertRaisesRegex(ValueError, "Decision No. 88, table 6, rule 34"):
            importer.parse_registry_export(raw)

    def test_pair_candidate_without_variant_id_is_explicitly_unlabelled(self):
        raw = _xml(ambiguous=False, include_sbkts=False).replace(
            b"<VehicleTypeVariantId>VAR-EXACT-01</VehicleTypeVariantId>", b""
        )
        parsed = importer.parse_registry_export(raw)
        variant = parsed["documents"][0]["variants"][0]
        self.assertIsNone(variant["variant_id"])
        self.assertEqual(variant["applicability_precision"], "approval_variant_unlabelled_candidate")
        self.assertEqual(len(variant["pair_candidates"]), 1)
        pair = variant["pair_candidates"][0]
        self.assertEqual(pair["applicability_precision"], "same_unlabelled_approval_variant_single_pair_candidate")
        self.assertEqual(pair["evidence_rule"], "single_engine_and_single_gearbox_code_nested_under_same_approval_variant_element")
        self.assertEqual(pair["verification_status"], "candidate_unverified")

    def test_sbkts_is_skipped_and_personal_or_vin_fields_are_not_parsed(self):
        parsed = importer.parse_registry_export(self.xml_path.read_bytes())
        self.assertEqual(parsed["skipped_sbkts"], 1)
        document = parsed["documents"][0]
        self.assertNotIn("Applicant Secret Synthetic", json.dumps(document, ensure_ascii=False))
        self.assertNotIn("VIN-SYNTHETIC-DO-NOT-STORE", json.dumps(document, ensure_ascii=False))
        self.assertNotIn("Test Certification Authority", json.dumps(document, ensure_ascii=False))
        self.assertNotIn("Test Vehicle Manufacturer", json.dumps(document, ensure_ascii=False))
        self.assertEqual(document["issuing_country_code"], "RU")
        self.assertEqual(document["market_scope"], ["EAEU"])
        self.assertIsNone(document["model_year"])

    def test_wrong_root_or_namespace_is_rejected(self):
        bad = f'<WrongRoot xmlns="{NS}"/>'.encode()
        with self.assertRaisesRegex(ValueError, "Expected"):
            importer.parse_registry_export(bad)
        bad_namespace = b'<ConformityVehicleDocsRegistryDetails xmlns="urn:wrong"/>'
        with self.assertRaisesRegex(ValueError, "Expected"):
            importer.parse_registry_export(bad_namespace)

    def test_dtd_and_entity_declarations_are_rejected(self):
        bad = f'<!DOCTYPE x [<!ENTITY e "x">]><ConformityVehicleDocsRegistryDetails xmlns="{NS}"/>'.encode()
        with self.assertRaisesRegex(ValueError, "DTD/entity"):
            importer.parse_registry_export(bad)

    def test_utf16_dtd_and_entity_declarations_are_rejected(self):
        bad = f'<!DOCTYPE x [<!ENTITY e "x">]><ConformityVehicleDocsRegistryDetails xmlns="{NS}"/>'.encode("utf-16")
        with self.assertRaisesRegex(ValueError, "DTD/entity"):
            importer.parse_registry_export(bad)

    def test_foreign_or_unqualified_schema_elements_are_rejected(self):
        original = b"<VehicleComponentModelCode>TEST-ENGINE-CODE-01</VehicleComponentModelCode>"
        replacements = (
            b'<evil:VehicleComponentModelCode xmlns:evil="urn:untrusted">TEST-ENGINE-CODE-01</evil:VehicleComponentModelCode>',
            b'<VehicleComponentModelCode xmlns="">TEST-ENGINE-CODE-01</VehicleComponentModelCode>',
        )
        for replacement in replacements:
            with self.subTest(replacement=replacement[:48]):
                bad = _xml(include_sbkts=False).replace(original, replacement, 1)
                with self.assertRaisesRegex(ValueError, "Unexpected XML element namespace"):
                    importer.parse_registry_export(bad)

    def test_unknown_document_kind_is_rejected(self):
        bad = _xml(include_sbkts=False).replace(b"<ConformityDocKindCode>30</ConformityDocKindCode>", b"<ConformityDocKindCode>99</ConformityDocKindCode>")
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            importer.parse_registry_export(bad)

    def test_validate_only_needs_no_reuse_rights_and_writes_nothing(self):
        result = importer.import_export(
            input_path=self.xml_path,
            source_manifest_path=self.manifest_path,
            retrieved_at=self.retrieved_at,
            validate_only=True,
        )
        self.assertEqual(result["status"], "validated_only")
        self.assertFalse(result["distribution_eligible"])
        self.assertFalse((self.root / "staging.sqlite").exists())

    def test_persistent_cache_is_blocked_without_written_permission(self):
        with self.assertRaisesRegex(ValueError, "permission_status"):
            importer.import_export(
                input_path=self.xml_path,
                source_manifest_path=self.manifest_path,
                retrieved_at=self.retrieved_at,
                output_path=self.root / "staging.sqlite",
                permission_evidence_path=self.root / "permission.pdf",
            )
        self.assertFalse((self.root / "staging.sqlite").exists())

    def test_persistent_staging_requires_matching_permission_evidence_and_stays_unverified(self):
        evidence = self.root / "permission.pdf"
        evidence.write_bytes(b"synthetic test permission evidence only")
        evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
        rights = {
            "permission_status": "approved_for_offline_distribution",
            "review_status": "approved_by_owner",
            "reviewed_at": "2026-11-06",
            "approval_reference": "SYNTHETIC-TEST-ONLY",
            "commercial_use_allowed": True,
            "bulk_reuse_allowed": True,
            "offline_cache_allowed": True,
            "display_and_redistribution_allowed": True,
            "permission_evidence": {
                "url": "https://example.invalid/synthetic-test-permission",
                "sha256": evidence_hash,
                "issuer": "synthetic test issuer",
            },
        }
        self.manifest_path.write_text(json.dumps(_source_manifest(rights), ensure_ascii=False), encoding="utf-8")
        output = self.root / "staging.sqlite"
        result = importer.import_export(
            input_path=self.xml_path,
            source_manifest_path=self.manifest_path,
            retrieved_at=self.retrieved_at,
            output_path=output,
            permission_evidence_path=evidence,
        )
        self.assertEqual(result["status"], "staging_created")
        self.assertFalse(result["distribution_eligible"])
        self.assertTrue(output.exists())
        self.assertTrue(Path(result["sidecar_manifest"]).exists())

        db = sqlite3.connect(output)
        try:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM approval_document").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM powertrain_pair_candidate").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT verification_status FROM powertrain_pair_candidate").fetchone()[0], "candidate_unverified")
            self.assertEqual(db.execute("SELECT applicability_precision FROM powertrain_pair_candidate").fetchone()[0], "same_approval_variant_id_single_pair_candidate")
            self.assertEqual(db.execute("SELECT rights_status FROM import_run").fetchone()[0], "owner_attested_not_independently_verified")
            self.assertEqual(db.execute("SELECT distribution_eligible FROM import_run").fetchone()[0], 0)
            columns = {
                row[1]
                for table in ("approval_document", "vehicle_variant", "engine_candidate", "transmission_candidate", "ecu_candidate")
                for row in db.execute(f"PRAGMA table_info({table})")
            }
            self.assertFalse(any(any(token in name.lower() for token in ("vin", "applicant", "authority_name", "manufacturer_name")) for name in columns))
            issuing_country, market_scope = db.execute("SELECT issuing_country_code, market_scope_json FROM approval_document").fetchone()
            self.assertEqual(issuing_country, "RU")
            self.assertEqual(json.loads(market_scope), ["EAEU"])
            stored_values = " ".join(str(row) for row in db.execute("SELECT * FROM approval_document"))
            self.assertNotIn("VIN-SYNTHETIC", stored_values)
            self.assertNotIn("Applicant Secret", stored_values)
            self.assertNotIn("Test Certification Authority", stored_values)
            self.assertNotIn("Test Vehicle Manufacturer", stored_values)
        finally:
            db.close()

    def test_permission_evidence_hash_mismatch_is_rejected(self):
        evidence = self.root / "permission.pdf"
        evidence.write_bytes(b"wrong synthetic evidence")
        rights = {
            "permission_status": "approved_for_offline_distribution",
            "review_status": "approved_by_owner",
            "reviewed_at": "2026-11-06",
            "approval_reference": "SYNTHETIC-TEST-ONLY",
            "commercial_use_allowed": True,
            "bulk_reuse_allowed": True,
            "offline_cache_allowed": True,
            "display_and_redistribution_allowed": True,
            "permission_evidence": {
                "url": "https://example.invalid/synthetic-test-permission",
                "sha256": "0" * 64,
                "issuer": "synthetic test issuer",
            },
        }
        self.manifest_path.write_text(json.dumps(_source_manifest(rights), ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            importer.import_export(
                input_path=self.xml_path,
                source_manifest_path=self.manifest_path,
                retrieved_at=self.retrieved_at,
                output_path=self.root / "staging.sqlite",
                permission_evidence_path=evidence,
            )

    def test_existing_output_is_never_overwritten(self):
        output = self.root / "existing.sqlite"
        output.write_bytes(b"do not overwrite")
        parsed = importer.parse_registry_export(self.xml_path.read_bytes())
        with self.assertRaises(FileExistsError):
            importer.write_staging_database(
                parsed,
                output_path=output,
                source=_source_manifest()["sources"][0],
                source_manifest_sha256="0" * 64,
                input_sha256="1" * 64,
                retrieved_at=self.retrieved_at,
                permission_evidence_sha256="2" * 64,
            )
        self.assertEqual(output.read_bytes(), b"do not overwrite")


if __name__ == "__main__":
    unittest.main()
