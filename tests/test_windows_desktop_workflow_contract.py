#!/usr/bin/env python3
"""Regression checks for Windows packaging and pinned research-pack alignment."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "windows-desktop-ci-run71.yml"


def main() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "  windows-2022-lifecycle:\n"
    if marker not in text:
        raise SystemExit("Windows Server 2022 lifecycle job is missing")

    job = text.split(marker, 1)[1]
    step_marker = "- name: Verify installer hashes and execute Windows Server 2022 lifecycle"
    if step_marker not in job:
        raise SystemExit("Windows Server 2022 verification step is missing")
    step = job.split(step_marker, 1)[1].split("\n      - name:", 1)[0]

    artifact_root = '$artifactRoot = Join-Path $env:RUNNER_TEMP "vag-tech-pro-run71-artifact/windows-lifecycle-staging"'
    desktop_root = '$desktopRoot = Join-Path $artifactRoot "desktop-source"'
    source_register = '$sourceRegisterPath = Join-Path $desktopRoot "data/source-manifests/vag-factory-source-register.json"'

    required = (artifact_root, desktop_root, source_register)
    missing = [needle for needle in required if needle not in step]
    if missing:
        raise SystemExit(f"Windows lifecycle script is missing required path setup: {missing}")

    positions = [step.index(needle) for needle in required]
    if positions != sorted(positions):
        raise SystemExit(
            "Windows lifecycle path variables must be initialized before use: "
            "artifactRoot -> desktopRoot -> sourceRegisterPath"
        )

    first_desktop_root_reference = step.index("$desktopRoot")
    if first_desktop_root_reference != positions[1]:
        raise SystemExit("desktopRoot is referenced before its initialization")

    if step.index('$lifecycle = Join-Path $desktopRoot "scripts/windows-installer-lifecycle.ps1"') < positions[1]:
        raise SystemExit("Lifecycle script path is resolved before desktopRoot initialization")

    package_manifest = json.loads((ROOT / "desktop-package-run35.json").read_text(encoding="utf-8"))
    build = package_manifest.get("build", {})
    resources = build.get("extraResources", [])
    if not any(item.get("from") == "data/source-manifests" and item.get("to") == "source-manifests" for item in resources if isinstance(item, dict)):
        raise SystemExit("Windows package does not include the source-rights register in extraResources")
    if build.get("afterPack") != "scripts/verify-source-register-after-pack.cjs":
        raise SystemExit("Windows package does not verify the packaged source-rights register afterPack")
    if "tests/source-register-after-pack.test.cjs" not in package_manifest.get("scripts", {}).get("test:desktop", ""):
        raise SystemExit("Source-register packaging tests are not part of the desktop test suite")
    apply_text = (ROOT / "apply-desktop-hardening-run35.cjs").read_text(encoding="utf-8")
    if "sourceRegisterVerifierPath" not in apply_text or "sourceRegisterTestPath" not in apply_text:
        raise SystemExit("Windows build does not generate the source-register afterPack verifier and tests")
    sync_marker = "      - name: Sync current source-rights register into desktop payload"
    if sync_marker not in text:
        raise SystemExit("Windows build does not synchronize the authoritative source-rights register")
    sync_step = text.split(sync_marker, 1)[1].split("      - name:", 1)[0]
    sync_required = (
        'python -m unittest discover -s tests -p "test_sync_vag_source_register_source_rights.py" -v',
        'python scripts/sync_vag_source_register.py --source "data/source-manifests/vag-factory-source-register.json" --desktop-root "desktop-source"',
        '$sync.status -ne "synced_verified"',
        '"vag_source_register_sha256=$($sync.sha256)"',
        '"vag_source_register_source_count=$($sync.source_count)"',
    )
    missing_sync = [needle for needle in sync_required if needle not in sync_step]
    if missing_sync:
        raise SystemExit(f"Source-rights register sync step is incomplete: {missing_sync}")

    desktop_tests_marker = "      - name: Run desktop, local core and research tests"
    installer_build_marker = "      - name: Build first Windows x64 NSIS installer"
    if desktop_tests_marker not in text or installer_build_marker not in text:
        raise SystemExit("Windows build is missing desktop tests or the NSIS installer build")
    if not (text.index(sync_marker) < text.index(desktop_tests_marker) < text.index(installer_build_marker)):
        raise SystemExit("Source-rights register must be synchronized before desktop tests and NSIS packaging")

    required_evidence = (
        'vag_source_register_sha256',
        'vag_source_register_source_count',
        'desktop-source/data/source-manifests/vag-factory-source-register.json',
        'data/source-manifests',
        'resources',
        'source-manifests',
        'sourceRegisterVerifierPath',
        'source-register-after-pack.test.cjs',
    )
    missing_evidence = [needle for needle in required_evidence if needle not in text and needle not in apply_text]
    if missing_evidence:
        raise SystemExit(f"Windows installer evidence does not cover the packaged source-rights register: {missing_evidence}")

    lifecycle_check = 'if ($metadata.vag_source_register_sha256 -ne $sourceRegisterActualHash'
    if lifecycle_check not in text:
        raise SystemExit("Windows Server 2022 lifecycle does not compare the staged source-register hash with build metadata")

    # The desktop workflow must consume the same immutable Wikidata snapshots
    # that the source manifests and integration scripts describe.
    model_source = json.loads((ROOT / "data/source-manifests/wikidata-vag-model-taxonomy.json").read_text(encoding="utf-8"))
    model_snapshot_id = model_source["source_revision"].removeprefix("wikidata-snapshot-")
    model_pack_path = ROOT / "data/research" / "wikidata-vag-taxonomy" / model_snapshot_id / "manifest.json"
    model_pack = json.loads(model_pack_path.read_text(encoding="utf-8"))
    model_artifact = model_source["source_artifact"]
    if model_source["database_sha256"] != model_pack["database_sha256"] or model_source["source_snapshot_sha256"] != model_pack["source_snapshot_sha256"]:
        raise SystemExit("Wikidata model source manifest does not match its immutable SQLite snapshot")
    if model_artifact["workflow_run_id"] != 42145993840 or model_artifact["artifact_id"] != 13469673252 or model_artifact["artifact_sha256"] != "f9ef2e5178e1dcdd92c0969a229c2e33a5608f14c9cf2f67ffc6f4baa21114e8":
        raise SystemExit("Wikidata model artifact provenance is not the current verified run")
    if model_pack["counts"]["model_entities"] != 521 or model_pack["counts"]["car_model_entities"] != 490 or model_pack["counts"]["car_model_series_entities"] != 40 or model_pack["counts"]["russian_labels"] != 285 or model_pack["counts"]["source_bindings"] != 530:
        raise SystemExit("Wikidata model snapshot counts drifted without a reviewed desktop integration update")
    taxonomy_script = (ROOT / "apply-wikidata-vag-taxonomy-run68.cjs").read_text(encoding="utf-8")
    if "counts: { models: wikidataCounts.models, carModelEntities: wikidataCounts.carModelEntities, carModelSeriesEntities: wikidataCounts.carModelSeriesEntities" not in taxonomy_script or "carModelEntities: 490, carModelSeriesEntities: 40" not in taxonomy_script:
        raise SystemExit("Desktop Wikidata summary does not expose both car-model and model-series class counts")

    generation_manifests = []
    for manifest_path in (ROOT / "data/research/wikidata-vag-generations").glob("*/manifest.json"):
        candidate = json.loads(manifest_path.read_text(encoding="utf-8"))
        if candidate.get("source_id") == "wikidata-vag-generation-candidates":
            generation_manifests.append((candidate.get("built_at_utc", ""), manifest_path, candidate))
    if not generation_manifests:
        raise SystemExit("No immutable Wikidata generation-candidate snapshot is present")
    _, generation_path, generation_pack = max(generation_manifests, key=lambda item: item[0])
    if generation_pack["parent_model_pack"]["database_sha256"] != model_pack["database_sha256"]:
        raise SystemExit("Latest Wikidata generation snapshot is not aligned to the current model taxonomy parent")
    generation_script = (ROOT / "scripts/integrate-wikidata-vag-generation-candidates.cjs").read_text(encoding="utf-8")
    generation_workflow_run = 42146307991
    generation_artifact_id = 13470966164
    generation_artifact_sha = "dc10b4b6b8a2f433802cc335e7c50f4f18e2642b9a09d0608b3de6e1b93d82bb"
    if f"workflowRunId: {generation_workflow_run}" not in generation_script or f"artifactId: {generation_artifact_id}" not in generation_script or generation_artifact_sha not in generation_script:
        raise SystemExit("Wikidata generation integration provenance is stale")
    if generation_pack["snapshot_id"] != "69cf847b7ef6" or generation_pack["counts"] != {"member_entities": 109, "model_member_links": 125, "source_bindings": 187, "models_with_members": 32, "manufacturers": 6, "russian_labels": 83, "date_statements": 155}:
        raise SystemExit("Wikidata generation candidate snapshot counts or revision changed without integration review")
    if f"snapshotId: \"{generation_pack['snapshot_id']}\"" not in generation_script or f"sourceSnapshotSha256: \"{generation_pack['source_snapshot_sha256']}\"" not in generation_script or f"sourceQuerySha256: \"{generation_pack['source_query_sha256']}\"" not in generation_script or f"databaseSha256: \"{generation_pack['database_sha256']}\"" not in generation_script:
        raise SystemExit("Wikidata generation integration hashes do not match the immutable snapshot")
    if f"run-id: {model_artifact['workflow_run_id']}" not in text or f"/runs/{model_artifact['workflow_run_id']}/artifacts" not in text or f"$artifact.id -eq {model_artifact['artifact_id']}" not in text or f"sha256:{model_artifact['artifact_sha256']}" not in text:
        raise SystemExit("Windows workflow is not downloading the current Wikidata model artifact")
    if f"run-id: {generation_workflow_run}" not in text or f"/runs/{generation_workflow_run}/artifacts" not in text or f"$artifact.id -eq {generation_artifact_id}" not in text or f"sha256:{generation_artifact_sha}" not in text:
        raise SystemExit("Windows workflow is not downloading the current Wikidata generation artifact")
    if generation_pack["parent_model_pack"]["snapshot_id"] != model_pack["snapshot_id"]:
        raise SystemExit("Wikidata generation pack parent snapshot does not match the installed model taxonomy")
    if "521 candidate entities (490 car-model class; 40 model-series class); 285 Russian-language labels; 6 manufacturers" not in (ROOT / "apply-wikidata-vag-taxonomy-run68.cjs").read_text(encoding="utf-8"):
        raise SystemExit("Desktop Wikidata taxonomy documentation has stale coverage counts")
    if "109 member entities, 125 model/member links, 187 source bindings" not in (ROOT / "README.md").read_text(encoding="utf-8"):
        raise SystemExit("README does not describe the current generation-candidate snapshot")
    stale_pins = ("41905383209", "13360765168", "a000a54572e57f9a50239f52ba6ef5d2dcb1088ebd394ce64e7fe051e71e2609", "41906770429", "13361576024", "0171d7775e9ad8c98ff564be1dd5729c85b031f67cd063521e5a9f4989ca3989", "5c1c7c37593b", "7a99f275966b", "39732875dff952041707a449168917c173c532db91a9950ec006a94ec9240a34")
    for stale in stale_pins:
        if stale in text or stale in generation_script:
            raise SystemExit(f"Stale Wikidata CI pin remains: {stale}")


    attribution_text = (ROOT / "data/research/wikidata-vag-taxonomy" / model_snapshot_id / "ATTRIBUTION.md").read_text(encoding="utf-8")
    if not re.search(r"not an authoritative\s+Volkswagen Group model register", attribution_text, flags=re.IGNORECASE):
        raise SystemExit("Wikidata attribution notice must preserve the candidate-only scope statement across line wrapping")
    if r"/not an authoritative\s+Volkswagen Group model register/i" not in (ROOT / "apply-wikidata-vag-taxonomy-run68.cjs").read_text(encoding="utf-8"):
        raise SystemExit("Wikidata pack validator is not whitespace-tolerant for the scope notice")

    lock_marker = "      - name: Generate, pin and install the Windows dependency lock"
    if lock_marker not in text:
        raise SystemExit("Windows dependency-lock security step is missing")
    lock_step = text.split(lock_marker, 1)[1].split("\n      - name:", 1)[0]
    for required_lock_guard in (
        "minimatch@^10.0.0",
        "'@electron/universal'",
        "'11.0.1'",
        "'electron-to-chromium'",
        "'1.5.478'",
        "npm install --no-save --no-audit --no-fund",
        "installed-dependency-verification.log",
        "installed-tree-matches-lock",
        "Dependency lock changed during clean installation",
        "minimatch-verification.log",
        "Vulnerable minimatch versions remain in the dependency lock",
        "npm audit --audit-level=moderate",
        "moderate or higher dependency vulnerabilities",
    ):
        if required_lock_guard not in lock_step:
            raise SystemExit(f"Windows dependency security gate is missing: {required_lock_guard}")
    if "npm ci --no-audit --no-fund" in lock_step:
        raise SystemExit("Windows dependency install must use the audited clean-install fallback for npm's scoped-overrides ci bug")
    if "k==='node_modules/minimatch'||k.endsWith('/node_modules/minimatch')" not in lock_step:
        raise SystemExit("Minimatch lock verifier must use literal package paths without an escaped regex")
    if "filter(([k])=>/(^|" + "\\\\/" + ")node_modules" in lock_step:
        raise SystemExit("Minimatch lock verifier contains an over-escaped regular expression")
    if "npm audit --audit-level=high" in lock_step:
        raise SystemExit("Full dependency audit must fail on moderate vulnerabilities, not only high/critical findings")

    package_manifest = json.loads((ROOT / "desktop-package-run35.json").read_text(encoding="utf-8"))
    extra_resources = package_manifest.get("build", {}).get("extraResources", [])
    for source_dir, target_dir in (("data/sql", "sql-schema"), ("data/schemas", "schemas")):
        if not any(item.get("from") == source_dir and item.get("to") == target_dir for item in extra_resources):
            raise SystemExit(f"Desktop package is missing extraResource {source_dir} -> {target_dir}")

    sync_script = (ROOT / "scripts/sync_vag_source_register.py").read_text(encoding="utf-8")
    for marker in ("source-manifest-index.json", "manifest_index_sha256", "os.replace"):
        if marker not in sync_script:
            raise SystemExit(f"Source manifest bundle sync is missing marker: {marker}")

    for marker in (
        "data/sql/**", "data/schemas/**", "tests/test_technical_library_schema.py",
        "tests/test_source_manifest_bundle.py", "source-manifest-index.json",
        "russian-eaeu-otts-sources.json", "vehicle-catalog.sql", "oem-dtc-index.sql",
        "dtc-catalog-links.sql", "technical-library.sql", "technical-record-payloads.schema.json",
        "source_manifest_index_sha256", "source_manifest_skipped_empty_files", "russian_eaeu_otts_manifest_sha256",
        "vehicle_catalog_sql_sha256", "oem_dtc_index_sql_sha256", "dtc_catalog_links_sql_sha256",
        "Verify packaged source manifests and technical library schemas",
        "vag-tech-pro-windows-x64-run71",
    ):
        if marker not in workflow:
            raise SystemExit(f"Windows workflow is missing technical-library packaging contract: {marker}")

    print("Windows desktop workflow contract: lifecycle paths, source-rights register and Wikidata snapshot pins are valid.")


if __name__ == "__main__":
    main()
