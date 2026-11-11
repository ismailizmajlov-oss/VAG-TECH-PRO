from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts import build_rdw_vag_research_pack as rdw

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data/source-manifests/rdw-eu-vag-type-approval-open-data.json"


class RdwVagResearchPackTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
        # Unit fixtures are intentionally independent from the pinned live RDW snapshot.
        self.source["snapshot"] = {
            "status": "not_downloaded_probe_only",
            "source_revision": None,
            "source_snapshot_sha256": None,
            "note": "Unit-test fixture; no live snapshot is claimed.",
        }
        self.source["source_snapshot_sha256"] = None
        self.source["hash_status"] = "unit_test_fixture_no_live_snapshot"
        self.source.pop("research_pack", None)
        self.source.pop("snapshot_refresh", None)
        self.source_bytes = (json.dumps(self.source, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.key = (
            "e1*2018/858*00403*07",
            "ACDUCAX0",
            "FD6FD6DD002PR4VNB50OO",
            "0",
        )
        self.datasets = {
            "registration": [{
                "merk": "VOLKSWAGEN",
                "handelsbenaming": "TAYRON",
                "typegoedkeuringsnummer": self.key[0],
                "variant": self.key[1],
                "uitvoering": self.key[2],
                "volgnummer_wijziging_eu_typegoedkeuring": self.key[3],
                "voertuigsoort": "Personenauto",
                "registration_count": "3",
            }],
            "tgk_drive": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevarianttgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "motorcode": "DUC",
                "typegoedkeuringsnummermotor": "E1*2018/858*00403*07",
                "aantalcilinders": "4",
                "cilinderinhoud": "1498",
            }],
            "tgk_gearbox": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevarianttgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "codetypeversnellingsbak": "A",
            }],
            "tgk_base": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevarianttgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "begindatumrevisieuitvoering": "2026-07-31",
                "voertuigcategorie": "M1",
            }],
            "tgk_make": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevarianttgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "merkcoderdw": "VWVP",
            }],
            "tgk_trade_name": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevariantgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "handelsbenamingfabrikant": "TAYRON",
                "typeaanduidingfabrikant": "R4",
            }],
        }
        self.metadata = {}
        for i, name in enumerate(rdw.DATASETS, start=1):
            required_columns = sorted(rdw.DATASETS[name]["required"])
            query_spec = {
                "dataset_id": rdw.DATASETS[name]["id"],
                "select": rdw.DATASETS[name]["select"],
                "fixture_scope": "unit-test-only",
                "market_scope": ["NL"],
            }
            self.metadata[name] = {
                "rows_updated_at": f"2026-11-06T00:00:0{i}Z",
                "view_last_modified": None,
                "source_columns_sha256": rdw.sha256_bytes(rdw.canonical_bytes(required_columns)),
                "required_columns": required_columns,
                "required_columns_sha256": rdw.sha256_bytes(rdw.canonical_bytes(required_columns)),
                "query_spec": query_spec,
            }

    def _metadata_payload(self, name: str, changed_revision: bool = False):
        required = sorted(rdw.DATASETS[name]["required"])
        return {
            "rowsUpdatedAt": (
                "2026-11-07T00:00:00Z" if changed_revision
                else self.metadata[name]["rows_updated_at"]
            ),
            "viewLastModified": self.metadata[name]["view_last_modified"],
            "columns": [{"fieldName": field} for field in required],
        }

    def test_committed_snapshot_and_refresh_hashes_are_valid_sha256(self):
        source = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
        groups = [source["snapshot"]["source_files"], source["snapshot_refresh"]["candidate_source_files"]]
        for group in groups:
            for item in group:
                for field in ("sha256", "source_columns_sha256", "required_columns_sha256", "query_spec_sha256"):
                    self.assertRegex(item[field], r"^[0-9a-f]{64}$", f"{item['dataset_id']}:{field}")

    def test_snapshot_manifest_entries_reject_malformed_sha256(self):
        item = {
            "dataset_id": "fixture", "dataset_name": "fixture", "source_revision": "1",
            "sha256": "a" * 64, "byte_size": 1, "row_count": 1,
            "source_columns_sha256": "b" * 60, "required_columns_sha256": "c" * 64,
            "query_spec_sha256": "d" * 64,
        }
        with self.assertRaisesRegex(ValueError, "Invalid RDW snapshot source_columns_sha256"):
            rdw.snapshot_manifest_entries([item])

    def test_source_revisions_and_schema_are_rechecked_after_acquisition(self):
        names_by_id = {str(config["id"]): name for name, config in rdw.DATASETS.items()}
        with patch.object(
            rdw,
            "fetch_metadata",
            side_effect=lambda dataset_id: self._metadata_payload(names_by_id[dataset_id]),
        ):
            rdw.verify_source_revisions(self.metadata)

    def test_numeric_revision_timestamps_are_normalized_for_sqlite_provenance(self):
        names_by_id = {str(config["id"]): name for name, config in rdw.DATASETS.items()}
        numeric_metadata = {}
        for index, (name, item) in enumerate(self.metadata.items(), start=1):
            numeric_metadata[name] = dict(item, rows_updated_at=1793949000 + index, view_last_modified=None)

        def numeric_payload(dataset_id):
            name = names_by_id[dataset_id]
            required = sorted(rdw.DATASETS[name]["required"])
            return {
                "rowsUpdatedAt": numeric_metadata[name]["rows_updated_at"],
                "viewLastModified": None,
                "columns": [{"fieldName": field} for field in required],
            }

        with patch.object(rdw, "fetch_metadata", side_effect=numeric_payload):
            rdw.verify_source_revisions(numeric_metadata)

        with tempfile.TemporaryDirectory() as tmp:
            rdw.build_pack(Path(tmp) / "pack", self.source, self.source_bytes, self.datasets, numeric_metadata)
            manifest = json.loads((Path(tmp) / "pack" / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(all(isinstance(value, str) for value in manifest["source_revisions"].values()))

    def test_sqlite_keeps_row_hashes_without_duplicating_raw_snapshot_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack_dir = Path(tmp) / "pack"
            report = rdw.build_pack(pack_dir, self.source, self.source_bytes, self.datasets, self.metadata)
            manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["source_row_storage_policy"],
                "canonical_jsonl_snapshots_external_and_sha256_verified; sqlite_source_rows_store_sha256_only",
            )
            db = sqlite3.connect(pack_dir / "rdw-vag-research.sqlite")
            try:
                columns = {row[1] for row in db.execute("PRAGMA table_info(source_rows)")}
                self.assertNotIn("raw_json", columns)
                self.assertEqual(
                    db.execute("SELECT count(*) FROM source_rows").fetchone()[0],
                    report["counts"]["source_rows"],
                )
                for item in manifest["source_files"]:
                    self.assertEqual(
                        db.execute("SELECT count(*) FROM source_rows WHERE dataset_id=?", (item["dataset_id"],)).fetchone()[0],
                        item["row_count"],
                    )
            finally:
                db.close()

    def test_dataset_revision_change_during_acquisition_is_rejected(self):
        names_by_id = {str(config["id"]): name for name, config in rdw.DATASETS.items()}

        def changed_metadata(dataset_id):
            name = names_by_id[dataset_id]
            return self._metadata_payload(name, changed_revision=(name == "registration"))

        with patch.object(rdw, "fetch_metadata", side_effect=changed_metadata):
            with self.assertRaisesRegex(RuntimeError, "changed during acquisition"):
                rdw.verify_source_revisions(self.metadata)

    def test_dataset_schema_change_during_acquisition_is_rejected(self):
        names_by_id = {str(config["id"]): name for name, config in rdw.DATASETS.items()}

        def changed_schema(dataset_id):
            name = names_by_id[dataset_id]
            payload = self._metadata_payload(name)
            payload["columns"] = [{"fieldName": "unexpected_schema_only"}]
            return payload

        with patch.object(rdw, "fetch_metadata", side_effect=changed_schema):
            with self.assertRaisesRegex(ValueError, "schema changed during acquisition"):
                rdw.verify_source_revisions(self.metadata)

    def test_sqlite_search_indexes_cover_scope_and_prefix_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            rdw.build_pack(pack, self.source, self.source_bytes, self.datasets, self.metadata)
            db = sqlite3.connect(pack / "rdw-vag-research.sqlite")
            try:
                indexes = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
                expected = {
                    "idx_registration_make_trade", "idx_registration_make", "idx_registration_trade_name",
                    "idx_registration_scope", "idx_approval_number", "idx_approval_variant", "idx_approval_version",
                    "idx_approval_revision", "idx_approval_exact_scope_key", "idx_engine_designation",
                    "idx_engine_scope", "idx_gearbox_classification", "idx_gearbox_scope",
                }
                self.assertTrue(expected.issubset(indexes))
            finally:
                db.close()

    def test_unreviewed_snapshot_refresh_is_rejected(self):
        pending = dict(self.source)
        pending["snapshot_refresh"] = {
            "status": "pending_candidate_reacquisition_and_review",
            "promotion_approved": False,
        }
        with self.assertRaisesRegex(ValueError, "not approved"):
            rdw.prepare_snapshot_manifest(pending, [])

    def test_reviewed_snapshot_refresh_requires_complete_nl_only_evidence(self):
        source_files = [{
            "dataset_id": "fixture-dataset",
            "dataset_name": "fixture",
            "source_revision": "1",
            "sha256": "a" * 64,
            "byte_size": 10,
            "row_count": 2,
            "source_columns_sha256": "b" * 64,
            "required_columns_sha256": "c" * 64,
            "query_spec_sha256": "d" * 64,
        }]
        entries = rdw.snapshot_manifest_entries(source_files)
        snapshot_sha = rdw.sha256_bytes(rdw.canonical_bytes(entries))
        revisions = {"fixture": "1"}
        source = dict(self.source)
        source["snapshot"] = {
            "status": "filtered_research_snapshot_acquired",
            "source_revision": revisions,
            "source_snapshot_sha256": snapshot_sha,
            "source_files": entries,
        }
        source["source_snapshot_sha256"] = snapshot_sha
        source["snapshot_refresh"] = {
            "status": "reviewed_snapshot_approved_for_nl_only_research_pack",
            "promotion_approved": True,
            "candidate_source_snapshot_sha256": snapshot_sha,
            "review_evidence": {
                "status": "independently_verified",
                "candidate_artifact_sha256": "1" * 64,
                "candidate_manifest_sha256": "2" * 64,
                "candidate_database_sha256": "3" * 64,
                "source_snapshot_sha256": snapshot_sha,
                "source_file_hashes_verified": 1,
                "source_file_sizes_and_row_counts_verified": 1,
                "source_row_hash_parity_verified": 1,
                "source_rows_verified": 2,
                "sqlite_integrity_check": "ok",
                "foreign_key_violations": 0,
                "forbidden_source_fields": 0,
                "market_scope": ["NL"],
                "production_import": False,
                "ru_eaeu_applicability": False,
                "exact_engine_gearbox_pair": False,
                "model_year_inferred": False,
                "generation_inferred": False,
            },
        }
        updated, actual_sha, actual_revisions = rdw.prepare_snapshot_manifest(source, source_files)
        self.assertEqual(actual_sha, snapshot_sha)
        self.assertEqual(actual_revisions, revisions)
        self.assertFalse(updated["data_ingested"])

        incomplete = dict(source)
        incomplete["snapshot_refresh"] = dict(source["snapshot_refresh"])
        incomplete["snapshot_refresh"]["review_evidence"] = dict(source["snapshot_refresh"]["review_evidence"])
        incomplete["snapshot_refresh"]["review_evidence"]["source_row_hash_parity_verified"] = 0
        with self.assertRaisesRegex(ValueError, "integrity gates"):
            rdw.prepare_snapshot_manifest(incomplete, source_files)

    def test_pinned_snapshot_manifest_rejects_changed_source_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            rdw.build_pack(first, self.source, self.source_bytes, self.datasets, self.metadata)
            pinned = json.loads((first / "rdw-eu-vag-type-approval-open-data.json").read_text(encoding="utf-8"))
            pinned["snapshot"]["source_snapshot_sha256"] = "0" * 64
            pinned["source_snapshot_sha256"] = "0" * 64
            pinned_bytes = (json.dumps(pinned, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            with self.assertRaisesRegex(RuntimeError, "source snapshot changed"):
                rdw.build_pack(Path(tmp) / "second", pinned, pinned_bytes, self.datasets, self.metadata)

    def test_pack_builds_hashed_sqlite_with_separate_engine_and_gearbox_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = rdw.build_pack(Path(tmp) / "pack", self.source, self.source_bytes, self.datasets, self.metadata)
            self.assertEqual(report["status"], "verified_research_only")
            self.assertFalse(report["ru_eaeu_applicability"])
            self.assertFalse(report["exact_engine_gearbox_pair_claim"])
            self.assertEqual(report["scope_coverage"], {
                "scopes_with_engine_and_gearbox_rows": 1,
                "engine_only_scopes": 0,
                "gearbox_only_scopes": 0,
                "scopes_with_multiple_engine_rows": 0,
                "scopes_with_multiple_gearbox_rows": 0,
                "unique_engine_designation_values": 1,
                "unique_gearbox_classification_values": 1,
                "missing_engine_designation_rows": 0,
                "missing_gearbox_classification_rows": 0,
            })
            pack = Path(tmp) / "pack"
            manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["market_scope"], ["NL"])
            self.assertEqual(manifest["source_snapshot_sha256"], report["source_snapshot_sha256"])
            self.assertEqual(manifest["source_revisions"], report["source_revisions"])
            self.assertEqual(len(manifest["search_indexes"]), 13)
            embedded_source = json.loads((pack / "rdw-eu-vag-type-approval-open-data.json").read_text(encoding="utf-8"))
            self.assertEqual(embedded_source["snapshot"]["status"], "filtered_research_snapshot_acquired")
            self.assertEqual(embedded_source["snapshot"]["source_snapshot_sha256"], manifest["source_snapshot_sha256"])
            self.assertEqual(embedded_source["source_snapshot_sha256"], manifest["source_snapshot_sha256"])
            self.assertEqual(len(embedded_source["snapshot"]["source_files"]), 6)
            self.assertFalse(embedded_source["data_ingested"])
            self.assertFalse(embedded_source["research_pack"]["production_import"])
            self.assertFalse(embedded_source["research_pack"]["ru_eaeu_applicability"])
            self.assertEqual(manifest["counts"]["source_files"], 6)
            self.assertEqual(manifest["counts"]["approval_scopes"], 1)
            self.assertEqual(manifest["counts"]["engine_candidates"], 1)
            self.assertEqual(manifest["counts"]["gearbox_classifications"], 1)
            self.assertEqual(manifest["scope_coverage"], report["scope_coverage"])
            self.assertIn("do not create or confirm", manifest["scope_coverage_semantics"])
            db = sqlite3.connect(pack / "rdw-vag-research.sqlite")
            try:
                tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertNotIn("engine_gearbox_pairs", tables)
                self.assertFalse(any("pair" in name.lower() for name in tables))
                self.assertEqual(db.execute("SELECT engine_designation FROM engine_designation_candidates").fetchone()[0], "DUC")
                self.assertEqual(db.execute("SELECT gearbox_type_classification FROM gearbox_classifications").fetchone()[0], "A")
                self.assertEqual(db.execute("SELECT count(*) FROM engine_designation_candidates WHERE verification_status='rdw_engine_designation_candidate_not_oem_confirmed'").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM gearbox_classifications WHERE verification_status='rdw_approval_gearbox_classification_not_vag_code'").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM approval_scope WHERE model_year IS NOT NULL OR generation IS NOT NULL").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM source_file_artifacts").fetchone()[0], 6)
                source_row_fk_targets = {row[2] for row in db.execute("PRAGMA foreign_key_list(source_rows)")}
                self.assertIn("source_file_artifacts", source_row_fk_targets)
                db.execute("PRAGMA foreign_keys=ON")
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(
                        "INSERT INTO source_rows VALUES (?,?,?,'NL')",
                        ("f" * 64, "unregistered-dataset", None),
                    )
                provenance = db.execute(
                    "SELECT source_columns_sha256, required_columns_sha256, query_spec_sha256, query_spec_json "
                    "FROM source_file_artifacts WHERE dataset_id=?",
                    (rdw.REGISTRATION_ID,),
                ).fetchone()
                registration_manifest = next(item for item in manifest["source_files"] if item["dataset_id"] == rdw.REGISTRATION_ID)
                self.assertEqual(
                    provenance[0],
                    rdw.sha256_bytes(rdw.canonical_bytes(sorted(rdw.DATASETS["registration"]["required"]))),
                )
                self.assertEqual(provenance[1], registration_manifest["required_columns_sha256"])
                self.assertEqual(provenance[2], registration_manifest["query_spec_sha256"])
                self.assertEqual(json.loads(provenance[3]), registration_manifest["query_spec"])
                self.assertEqual(
                    rdw.sha256_bytes(rdw.canonical_bytes(registration_manifest["query_spec"])),
                    registration_manifest["query_spec_sha256"],
                )
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            finally:
                db.close()

    def test_multiple_engine_rows_in_one_scope_are_reported_not_paired(self):
        datasets = json.loads(json.dumps(self.datasets))
        extra_engine_row = dict(datasets["tgk_drive"][0])
        extra_engine_row["motorcode"] = "SECOND-CANDIDATE"
        datasets["tgk_drive"].append(extra_engine_row)
        with tempfile.TemporaryDirectory() as tmp:
            report = rdw.build_pack(Path(tmp) / "pack", self.source, self.source_bytes, datasets, self.metadata)
            self.assertEqual(report["scope_coverage"]["scopes_with_engine_and_gearbox_rows"], 1)
            self.assertEqual(report["scope_coverage"]["scopes_with_multiple_engine_rows"], 1)
            self.assertFalse(report["exact_engine_gearbox_pair_claim"])
            manifest = json.loads((Path(tmp) / "pack" / "manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["pair_table_created"])
            db = sqlite3.connect(Path(tmp) / "pack" / "rdw-vag-research.sqlite")
            try:
                self.assertEqual(
                    db.execute("SELECT count(*) FROM engine_designation_candidates").fetchone()[0],
                    2,
                )
            finally:
                db.close()

    def test_snapshot_rows_must_match_sqlite_source_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            rdw.build_pack(pack, self.source, self.source_bytes, self.datasets, self.metadata)
            manifest_path = pack / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = manifest["source_files"][0]
            snapshot_path = pack / item["path"]
            snapshot_rows = [
                json.loads(line)
                for line in snapshot_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            snapshot_rows[0]["tampered_after_download"] = True
            snapshot_bytes = b"".join(rdw.canonical_bytes(row) + b"\n" for row in snapshot_rows)
            snapshot_path.write_bytes(snapshot_bytes)
            item["sha256"] = rdw.sha256_bytes(snapshot_bytes)
            item["byte_size"] = len(snapshot_bytes)

            database_path = pack / manifest["database"]["path"]
            db = sqlite3.connect(database_path)
            try:
                db.execute(
                    "UPDATE source_file_artifacts SET source_snapshot_sha256=?, byte_size=? WHERE dataset_id=?",
                    (item["sha256"], item["byte_size"], item["dataset_id"]),
                )
                db.commit()
            finally:
                db.close()
            manifest["database"]["sha256"] = rdw.sha256_file(database_path)
            manifest["database"]["byte_size"] = database_path.stat().st_size
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "snapshot/SQLite source rows differ"):
                rdw.validate_pack(pack)

    def test_scope_coverage_manifest_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            rdw.build_pack(pack, self.source, self.source_bytes, self.datasets, self.metadata)
            manifest_path = pack / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["scope_coverage"]["scopes_with_engine_and_gearbox_rows"] = 999
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "scope-coverage metrics differ from SQLite"):
                rdw.validate_pack(pack)

    def test_query_spec_digest_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            rdw.build_pack(pack, self.source, self.source_bytes, self.datasets, self.metadata)
            manifest_path = pack / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_files"][0]["query_spec"]["where_template"] = "unreviewed query"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "query-spec provenance hash mismatch"):
                rdw.validate_pack(pack)

    def test_rights_gate_fails_closed(self):
        bad = json.loads(json.dumps(self.source))
        bad["rights"]["offline_cache_allowed"] = False
        with self.assertRaisesRegex(ValueError, "offline_cache_allowed"):
            rdw.validate_source_manifest(bad)

    def test_wrong_market_or_production_import_fails_closed(self):
        bad = json.loads(json.dumps(self.source))
        bad["market_scope"] = ["RU"]
        with self.assertRaisesRegex(ValueError, "NL-scoped"):
            rdw.validate_source_manifest(bad)
        bad = json.loads(json.dumps(self.source))
        bad["import_policy"]["production_import"] = True
        with self.assertRaisesRegex(ValueError, "research-only"):
            rdw.validate_source_manifest(bad)

    def test_forbidden_registration_and_personal_fields_are_rejected_recursively(self):
        with self.assertRaisesRegex(ValueError, "kenteken"):
            rdw.reject_forbidden_fields({"safe": [{"kenteken": "XX-123-X"}]})
        with self.assertRaisesRegex(ValueError, "(?i)vin"):
            rdw.reject_forbidden_fields({"Vehicle": {"VIN": "not-stored"}})

    def test_exact_scope_requires_approval_variant_version_and_revision(self):
        self.assertEqual(rdw.scope_key({
            "typegoedkeuringsnummer": self.key[0],
            "codevarianttgk": self.key[1],
            "codeuitvoeringtgk": self.key[2],
            "volgnummerrevisieuitvoering": self.key[3],
        }, "codevarianttgk"), self.key)
        self.assertIsNone(rdw.scope_key({
            "typegoedkeuringsnummer": self.key[0],
            "codevarianttgk": self.key[1],
            "codeuitvoeringtgk": "",
            "volgnummerrevisieuitvoering": self.key[3],
        }, "codevarianttgk"))

    def test_soql_literal_escapes_quotes_and_dataset_ids_are_constrained(self):
        self.assertEqual(rdw.soql_literal("A'B"), "'A''B'")
        with self.assertRaisesRegex(ValueError, "Invalid RDW dataset id"):
            rdw.build_soda_url("m9d7-ebf2/evil", {"$limit": "1"})
        url = rdw.build_soda_url("m9d7-ebf2", {"$select": "merk,handelsbenaming", "$limit": "1"})
        self.assertIn("%24select", url)
        self.assertNotIn("kenteken", url.lower())

    def test_child_row_without_exact_registration_scope_is_rejected(self):
        bad_datasets = json.loads(json.dumps(self.datasets))
        bad_datasets["tgk_drive"][0]["codeuitvoeringtgk"] = "OTHER"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "no exact matching registration approval scope"):
                rdw.build_pack(Path(tmp) / "pack", self.source, self.source_bytes, bad_datasets, self.metadata)




class WindowsBuildMetadataContractTests(unittest.TestCase):
    def test_windows_build_metadata_pins_integrated_rdw_pack_provenance_and_scope(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "windows-desktop-ci-run71.yml").read_text(encoding="utf-8")
        required_contract = (
            "$rdwResearchManifest.packs | Where-Object { $_.id -eq \"rdw-vag-nl-eu-type-approval-research\" }",
            "Resolve-RdwResearchFile",
            "$rdwEntry.database_sha256",
            "$rdwEntry.pack_manifest_sha256",
            "$rdwEntry.source_manifest_sha256",
            "$rdwEntry.desktop_integration_report_sha256",
            "$rdwIntegrationReport.source_run_id",
            "$rdwIntegrationReport.artifact_sha256",
            "rdw_source_artifact_sha256 = $rdwArtifactHash",
            "rdw_source_snapshot_sha256 = $rdwSnapshotHash",
            "rdw_pack_manifest_sha256 = $rdwPackManifestHash",
            "rdw_database_sha256 = $rdwDatabaseHash",
            "rdw_integration_report_sha256 = $rdwIntegrationReportHash",
            "rdw_approval_scope_count = $rdwApprovalScopeCount",
            "rdw_engine_candidate_count = $rdwEngineCount",
            "rdw_gearbox_classification_count = $rdwGearboxCount",
            "rdw_production_import = $rdwProductionImport",
            "rdw_product_import_allowed = $rdwProductImportAllowed",
            "rdw_data_ingested = $rdwDataIngested",
            "rdw_ru_eaeu_applicability = $rdwRuEaeuApplicability",
            "rdw_exact_engine_gearbox_pair = $rdwExactEngineGearboxPair",
            "rdw_diagnostic_execution_allowed = $rdwDiagnosticExecutionAllowed",
        )
        for token in required_contract:
            with self.subTest(token=token):
                self.assertIn(token, workflow)

    def test_rdw_build_metadata_fails_closed_for_market_and_fitment_claims(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "windows-desktop-ci-run71.yml").read_text(encoding="utf-8")
        self.assertIn('$rdwEntry.market_scope[0] -ne "NL"', workflow)
        self.assertIn("$rdwEntry.production_import -ne $false", workflow)
        self.assertIn("$rdwEntry.ru_eaeu_applicability -ne $false", workflow)
        self.assertIn("$rdwEntry.exact_vehicle_fitment -ne $false", workflow)
        self.assertIn("$rdwEntry.exact_engine_gearbox_pair -ne $false", workflow)
        self.assertIn("$rdwEntry.repair_applicability -ne $false", workflow)
        self.assertIn("$rdwEntry.diagnostic_execution_allowed -ne $false", workflow)

if __name__ == "__main__":
    unittest.main()
