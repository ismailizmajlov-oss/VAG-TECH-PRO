#!/usr/bin/env python3
"""Regression checks for Windows packaging and pinned research-pack alignment."""

import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "windows-desktop-ci-run71.yml"
NATIVE_WORKFLOW = ROOT / ".github" / "workflows" / "windows-10-11-native-lifecycle.yml"


def main() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    native_text = NATIVE_WORKFLOW.read_text(encoding="utf-8")
    desktop_workflow_name = re.search(r"(?m)^name:\s*(.+?)\s*$", text)
    native_trigger = re.search(
        r"(?ms)^on:\s*\n\s+workflow_run:\s*\n\s+workflows:\s*\n(?P<items>(?:\s+-\s+.*\n)+)",
        native_text,
    )
    if not desktop_workflow_name or not native_trigger:
        raise SystemExit("Native Windows 10/11 workflow must listen to the desktop workflow_run event")
    upstream_names = re.findall(r"(?m)^\s+-\s+(.+?)\s*$", native_trigger.group("items"))
    if desktop_workflow_name.group(1) not in upstream_names:
        raise SystemExit(
            "Native Windows 10/11 lifecycle trigger does not match the current desktop workflow name: "
            + desktop_workflow_name.group(1)
        )
    status_workflow = re.search(r'(?m)^\s+upstream_workflow\s*=\s*"([^"]+)"', native_text)
    actual_status_workflow = status_workflow.group(1) if status_workflow else "<missing>"
    if actual_status_workflow != desktop_workflow_name.group(1):
        raise SystemExit(
            "Native Windows status record must identify the exact upstream desktop workflow; "
            f"expected {desktop_workflow_name.group(1)!r}, found {actual_status_workflow!r}"
        )
    if "windows-lifecycle-staging/desktop-source/lib/local-research-db.cjs" not in text:
        raise SystemExit("Windows audit artifact must include the local research verifier source")
    if "windows-lifecycle-staging/desktop-source/data/research/obdb-vag-signals-cc-by-sa/manifest.json" not in text:
        raise SystemExit("Windows audit artifact must include the exact OBDb pack manifest")
    if "group: vag-tech-pro-windows-x64-v3-${{ github.ref }}" not in text:
        raise SystemExit("Windows validation workflow must use the v3 concurrency group to bypass stale v2 runs")
    if "cancel-in-progress: true" not in text:
        raise SystemExit("Windows validation workflow must cancel superseded runs so the latest source snapshot is tested first")
    status_retry_contract = (
        "$published = $false",
        "for ($attempt = 1; $attempt -le 5; $attempt++)",
        "git fetch origin main",
        "git rebase origin/main",
        "git push origin HEAD:main",
        "Status publication attempt $attempt lost a concurrent main update",
        "Could not publish the Windows validation status record after five concurrent-update retries.",
    )
    missing_status_retry = [marker for marker in status_retry_contract if marker not in native_text]
    if missing_status_retry or "git pull --rebase origin main" in native_text:
        raise SystemExit(f"Native Windows status recorder must retry concurrent main updates safely: {missing_status_retry}")
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
    lint_script = package_manifest.get("scripts", {}).get("lint", "")
    for ignored in ('--ignore-pattern "release/**"', '--ignore-pattern ".next/**"', '--ignore-pattern "out/**"', '--ignore-pattern "coverage/**"'):
        if ignored not in lint_script:
            raise SystemExit(f"Desktop lint must exclude generated output: {ignored}")
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
    lifecycle_patch_markers = (
        "windows-installer-lifecycle.ps1",
        "Start-DesktopAndWait must not leak diagnostic text",
        "System.Collections.IDictionary",
        "windows-lifecycle-script-contract.test.cjs",
        "incidental pipeline output",
    )
    missing_lifecycle_patch = [item for item in lifecycle_patch_markers if item not in apply_text]
    if missing_lifecycle_patch:
        raise SystemExit(f"Windows lifecycle return-pipeline regression patch is incomplete: {missing_lifecycle_patch}")
    status_output_guard = (
        "const astraStatusOutput =",
        "const astraStatusSafe =",
        "const astraStatusVerbose =",
        "astraOutputCount === 1 && astraHostCount === 0 && astraVerboseCount === 0",
        "astraHostCount + astraVerboseCount > 1",
        "(astraOutputCount !== 0 && astraHostCount + astraVerboseCount !== 0)",
        "ASTRA lifecycle status message is duplicated or writes to the success pipeline.",
    )
    missing_status_output_guard = [item for item in status_output_guard if item not in apply_text]
    if missing_status_output_guard:
        raise SystemExit(f"Windows lifecycle patch must accept an existing safe Write-Host/Write-Verbose line and reject pipeline output: {missing_status_output_guard}")
    hardening_call = "node apply-desktop-hardening-run35.cjs"
    hardening_guard = 'if ($LASTEXITCODE -ne 0) { throw "Desktop hardening run35 patch failed" }'
    local_core_check = "node --check apply-local-core-host-origin-run51.cjs"
    if not (hardening_call in text and hardening_guard in text and local_core_check in text):
        raise SystemExit("Windows workflow must fail immediately when the run35 hardening patch exits non-zero")
    if not (text.index(hardening_call) < text.index(hardening_guard) < text.index(local_core_check)):
        raise SystemExit("Windows run35 hardening exit-code guard must be immediately after the patch and before the next script")
    kba_path_markers = (
        "data/source-manifests/kba-de-whole-vehicle-type-approvals.json",
        "data/source-manifests/kba-de-fz-hersteller-handelsnamen-pkw.json",
        "docs/KBA_GERMANY_OPEN_DATA_REVIEW_2026-11-07.md",
    )
    missing_kba_paths = [marker for marker in kba_path_markers if text.count(marker) < 2]
    if missing_kba_paths:
        raise SystemExit(f"KBA source changes must trigger both push and pull-request validation: {missing_kba_paths}")
    kyrgyz_review_path = "docs/research/KYRGYZ_SINGLE_WINDOW_PUBLIC_REGISTRY_REVIEW_2026-11-07.md"
    if text.count(kyrgyz_review_path) < 2:
        raise SystemExit("Kyrgyz public-registry review must trigger both push and pull-request validation")
    if text.count("tests/test_russian_eaeu_otts_manifest.py") < 3:
        raise SystemExit("Russian/EAEU source-manifest tests must run and be covered by both push/PR path filters")
    armenia_rights_test = "tests/test_armstandard_registry_rights_gate.py"
    if text.count(armenia_rights_test) < 3 or "python tests/test_armstandard_registry_rights_gate.py" not in text:
        raise SystemExit("Armenian OTTS rights quarantine test must run and be covered by both push/PR path filters")
    if text.index("python tests/test_armstandard_registry_rights_gate.py") > text.index("$syncOutput = python scripts/sync_vag_source_register.py"):
        raise SystemExit("Armenian OTTS rights quarantine test must run before source-register synchronization")

    research_manifest_contract = (
        '$researchManifestPath = "desktop-source/data/research/manifest.json"',
        '$researchPackIds = @($researchManifest.packs | ForEach-Object { [string]$_.id })',
        '$uniqueResearchPackIds = @($researchPackIds | Sort-Object -Unique)',
        '$researchManifestEntries = $researchPackIds.Count',
        '$researchManifestSha = (Get-FileHash -LiteralPath $researchManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()',
        'research_manifest_entries=$researchManifestEntries; research_manifest_sha256=$researchManifestSha;',
    )
    missing_research_manifest_contract = [marker for marker in research_manifest_contract if marker not in text]
    if missing_research_manifest_contract or "research_manifest_entries=10;" in text:
        raise SystemExit(f"Windows source audit must derive research pack counts and hash from the current manifest: {missing_research_manifest_contract}")

    generation_count_contract = (
        "members=$($evidence.counts.member_entities)",
        "model_member_links=$($evidence.counts.model_member_links)",
        "source_bindings=$($evidence.counts.source_bindings)",
        "models_with_members=$($evidence.counts.models_with_members)",
        "manufacturers=$($evidence.counts.manufacturers)",
        "russian_labels=$($evidence.counts.russian_labels)",
        "date_statements=$($evidence.counts.date_statements)",
    )
    missing_generation_count_contract = [marker for marker in generation_count_contract if marker not in text]
    if missing_generation_count_contract or "members=9; model_member_links=10; source_bindings=14;" in text:
        raise SystemExit(f"Windows source audit must print the actual Wikidata generation evidence counts: {missing_generation_count_contract}")
    if text.count("tests/test_kba_germany_open_data_source_rights.py") < 3 or "python tests/test_kba_germany_open_data_source_rights.py" not in text:
        raise SystemExit("KBA source-rights test must run and be covered by both push/PR path filters")
    if "python tests/test_decode_tr_source_rights.py" not in text:
        raise SystemExit("Windows source-rights gate does not execute the decode.tr quarantine test")
    if text.count('tests/test_decode_tr_source_rights.py') < 3:
        raise SystemExit("decode.tr rights test must be covered by both push/PR path filters and the validation step")
    if text.count('docs/research/DECODE_TR_VAG_ENGINE_DRIVETRAIN_RIGHTS_REVIEW_2026-11-06.md') < 2:
        raise SystemExit("decode.tr rights review must trigger both push and pull-request validation")
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
    metadata_step_marker = "      - name: Write build metadata"
    metadata_upload_marker = "      - name: Upload standalone build metadata for independent installer hash verification"
    inventory_step_marker = "      - name: Create desktop source inventory for technical-section audit"
    if metadata_step_marker not in text or metadata_upload_marker not in text or inventory_step_marker not in text:
        raise SystemExit("Windows CI must generate and publish standalone build metadata before source inventory packaging")
    metadata_upload_step = text.split(metadata_upload_marker, 1)[1].split("\n      - name:", 1)[0]
    metadata_upload_required = (
        "hashFiles('build-metadata.json') != ''",
        "vag-tech-pro-build-metadata-${{ github.run_id }}",
        "path: build-metadata.json",
        "if-no-files-found: error",
        "retention-days: 30",
    )
    missing_metadata_upload = [marker for marker in metadata_upload_required if marker not in metadata_upload_step]
    if missing_metadata_upload:
        raise SystemExit(f"Standalone build metadata artifact contract is incomplete: {missing_metadata_upload}")
    if "Create desktop source inventory for technical-section audit" in metadata_upload_step:
        raise SystemExit("Standalone build metadata upload step boundary extends into the following workflow step")
    if not (text.index(metadata_step_marker) < text.index(metadata_upload_marker) < text.index(inventory_step_marker)):
        raise SystemExit("Standalone build metadata must be uploaded immediately after it is generated")

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
    if f"run-id: {model_artifact['workflow_run_id']}" not in text or f"/runs/{model_artifact['workflow_run_id']}/artifacts" not in text or f"$_.id -eq {model_artifact['artifact_id']}" not in text or f"sha256:{model_artifact['artifact_sha256']}" not in text:
        raise SystemExit("Windows workflow is not downloading the current Wikidata model artifact")
    if f"run-id: {generation_workflow_run}" not in text or f"/runs/{generation_workflow_run}/artifacts" not in text or f"$_.id -eq {generation_artifact_id}" not in text or f"sha256:{generation_artifact_sha}" not in text:
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
        if marker not in text:
            raise SystemExit(f"Windows workflow is missing technical-library packaging contract: {marker}")

    patch_set_line = next((line for line in text.splitlines() if "patch_set = " in line), "")
    required_patch_set = (
        "run76-desktop-row-types-fix",
        "run77-lifecycle-session-output",
        "run78-rdw-ui-contract",
        "run79-typed-technical-payload-renderer",
        "run80-technical-payload-schema-validation",
        "run81-strict-dtc-oem-supersession-validation",
        "run91-obdex-dtc-research-range-quarantine",
    )
    missing_patch_set = [marker for marker in required_patch_set if marker not in patch_set_line]
    if missing_patch_set:
        raise SystemExit(f"Windows build metadata patch_set omits applied desktop changes: {missing_patch_set}")

    offline_entry_paths = (
        "apply-desktop-offline-entry-run90.cjs",
        "desktop-offline-route-run90.tsx",
        "desktop-offline-route-test-run90.cjs",
        "tests/desktop-offline-entry-patch-run90.test.cjs",
    )
    missing_offline_entry_paths = [marker for marker in offline_entry_paths if text.count(marker) < 2]
    if missing_offline_entry_paths:
        raise SystemExit(f"Offline desktop entry changes must trigger both push and pull-request validation: {missing_offline_entry_paths}")
    offline_entry_marker = "      - name: Apply dedicated offline desktop entry and isolate cloud credentials (run90)"
    if offline_entry_marker not in text:
        raise SystemExit("Windows workflow does not apply the dedicated offline SQLite desktop entry")
    offline_entry_step = text.split(offline_entry_marker, 1)[1].split("\n      - name:", 1)[0]
    for required_offline_entry_step in (
        "node --test tests/desktop-offline-entry-patch-run90.test.cjs",
        "node apply-desktop-offline-entry-run90.cjs",
        "node --test desktop-source/tests/desktop-offline-entry-run90.test.cjs",
        "cloud_credentials_forwarded=false",
        "scripts/patches/apply-desktop-offline-entry-run90.cjs",
    ):
        if required_offline_entry_step not in offline_entry_step:
            raise SystemExit(f"Dedicated offline desktop entry step is incomplete: {required_offline_entry_step}")
    if not text.index(offline_entry_marker) < text.index(desktop_tests_marker) < text.index(installer_build_marker):
        raise SystemExit("Dedicated offline desktop entry must be applied and tested before desktop tests and NSIS packaging")

    run91_paths = (
        "apply-dtc-research-range-quarantine-run91.cjs",
        "tests/dtc-research-range-quarantine.test.cjs",
        "docs/research/OBDEX_DTC_NAMESPACE_QUARANTINE_RUN91.md",
    )
    missing_run91_paths = [marker for marker in run91_paths if text.count(marker) < 2]
    if missing_run91_paths:
        raise SystemExit(f"Run91 DTC quarantine changes must trigger push and pull-request validation: {missing_run91_paths}")
    run91_marker = "      - name: Quarantine unresolved OBDex DTC namespace ranges in research UI (run91)"
    if run91_marker not in text:
        raise SystemExit("Windows workflow does not apply the run91 OBDex DTC namespace quarantine patch")
    run91_step = text.split(run91_marker, 1)[1].split("\n      - name:", 1)[0]
    for required_run91_step in (
        "node --check apply-dtc-research-range-quarantine-run91.cjs",
        "node apply-dtc-research-range-quarantine-run91.cjs --desktop-root desktop-source",
        "node --test desktop-source/tests/dtc-research-range-quarantine.test.cjs",
        "scripts/patches/apply-dtc-research-range-quarantine-run91.cjs",
        "unresolved_ranges_quarantined=true",
        "production_import=false",
        "policy_resource=app-runtime/data/policies",
    ):
        if required_run91_step not in run91_step:
            raise SystemExit(f"Run91 DTC quarantine workflow step is incomplete: {required_run91_step}")
    if not text.index(run91_marker) < text.index(desktop_tests_marker) < text.index(installer_build_marker):
        raise SystemExit("Run91 DTC quarantine patch and tests must run before the full desktop suite and NSIS packaging")
    metadata_run91 = text.split("      - name: Write build metadata", 1)[1].split("\n      - name:", 1)[0]
    if "dtc_research_range_quarantine_patch_sha256 = $dtcResearchQuarantinePatchHash;" not in metadata_run91 or 'Get-FileHash -LiteralPath $dtcResearchQuarantinePatchPath' not in metadata_run91:
        raise SystemExit("Build metadata must bind the run91 DTC quarantine patch SHA-256")
    for artifact_marker in (
        "apply-dtc-research-range-quarantine-run91.cjs",
        "dtc-research-range-quarantine-run91.log",
        "dtc-research-range-quarantine-run91-tests.log",
        "windows-lifecycle-staging/desktop-source/scripts/patches/apply-dtc-research-range-quarantine-run91.cjs",
    ):
        if artifact_marker not in text:
            raise SystemExit(f"Run91 DTC quarantine evidence artifact is missing: {artifact_marker}")
    cleanup_patch = (ROOT / "apply-local-core-test-cleanup-run75.cjs").read_text(encoding="utf-8")
    rights_fixture = 'generation_name:"Golf VII",market_scope:"RU",model_year:2017,engine_code_declared:"CZEA",transmission_code_declared:"DQ200",nickname:"Rights test"'
    if rights_fixture not in cleanup_patch or "rights-revocation fixture exact generation" not in cleanup_patch:
        raise SystemExit("Rights-revocation regression fixture must declare the exact generation required by the manual vehicle identity gate")

    metadata_marker = "      - name: Write build metadata"
    metadata_step_for_offline = text.split(metadata_marker, 1)[1].split("\n      - name:", 1)[0]
    if "desktop_offline_entry = 'app/desktop'" not in metadata_step_for_offline or "desktop_offline_entry_patch_sha256" not in metadata_step_for_offline:
        raise SystemExit("Build metadata does not bind the dedicated offline entry and its patch hash")



    rdw_step_marker = "      - name: Resolve latest successful RDW NL/EU research pack compatible with pinned manifest"
    if rdw_step_marker not in text:
        raise SystemExit("Windows workflow is missing the current RDW pack resolver")
    rdw_step = text.split(rdw_step_marker, 1)[1].split("\n      - name:", 1)[0]
    rdw_required = (
        '$successfulRuns = @($response.workflow_runs | Where-Object { $_.head_branch -eq "main" -and $_.status -eq "completed" -and $_.conclusion -eq "success" -and $_.event -in @("push", "workflow_dispatch") } | Sort-Object run_number -Descending)',
        '$run = $successfulRuns | Select-Object -First 1',
        '$latestObservedRun = $response.workflow_runs | Sort-Object run_number -Descending | Select-Object -First 1',
        'using latest successful run',
        'source-manifest and snapshot hashes to the pinned repository manifest',
        '$digest = ([string]$artifact.digest -replace "^sha256:", "").ToLowerInvariant()',
        '$digest -notmatch "^[a-f0-9]{64}$"',
    )
    missing_rdw_contract = [marker for marker in rdw_required if marker not in rdw_step]
    if missing_rdw_contract:
        raise SystemExit(f"RDW resolver must select a completed successful run and verify its pinned artifact digest: {missing_rdw_contract}")
    if not re.search(r"(?m)^\s+timeout-minutes:\s+\d+", text):
        raise SystemExit("Windows build job must retain an explicit bounded timeout")

    if "name: Create desktop source inventory for technical-section audit" not in text:
        raise SystemExit("Desktop source technical-surface inventory step is missing")
    if "desktop-source-technical-surface.txt" not in text or "desktop-source-inventory.txt" not in text:
        raise SystemExit("Desktop source inventory evidence is not uploaded")
    source_inventory_contract = (
        '$excludedSegments = @("node_modules", ".next", "release", "out", "coverage", "dist", "build", ".turbo", ".cache")',
        "$segments = $relative -split '[\\\\/]+'",
        '-not ($segments | Where-Object { $excludedSegments -contains $_ })',
    )
    missing_source_inventory_contract = [marker for marker in source_inventory_contract if marker not in text]
    if missing_source_inventory_contract:
        raise SystemExit(f"Desktop source audit must exclude generated directory trees by path segment: {missing_source_inventory_contract}")
    if "Upload desktop source audit evidence" not in text or "vag-tech-pro-desktop-source-audit-" not in text:
        raise SystemExit("Small desktop source audit artifact is not uploaded independently")
    audit_copy_match = re.search(
        r"(?ms)^      - name: Mirror patched desktop source and ASTRA integration into audit staging\n(?P<step>.*?)(?=^      - name:|\Z)",
        text,
    )
    if not audit_copy_match:
        raise SystemExit("Desktop source audit mirror step is missing")
    audit_copy_step = audit_copy_match.group("step")
    for required_audit_file in ('"package.json"', '"package-lock.json"', '"scripts/prepare-electron-runtime.cjs"'):
        if required_audit_file not in audit_copy_step:
            raise SystemExit(f"Desktop source audit artifact omits runtime packaging evidence: {required_audit_file}")

    audit_upload_marker = "      - name: Upload desktop source audit evidence"
    if audit_upload_marker not in text:
        raise SystemExit("Desktop source audit artifact upload step is missing")
    audit_upload_step = text.split(audit_upload_marker, 1)[1].split("\n      - name:", 1)[0]
    for required_audit_path in (
        "windows-lifecycle-staging/desktop-source/package.json",
        "windows-lifecycle-staging/desktop-source/package-lock.json",
        "windows-lifecycle-staging/desktop-source/scripts/prepare-electron-runtime.cjs",
    ):
        if required_audit_path not in audit_upload_step:
            raise SystemExit(f"Desktop source audit artifact does not publish runtime packaging evidence: {required_audit_path}")
    if "Create desktop source inventory for technical-section audit" in audit_upload_step:
        raise SystemExit("Desktop source audit upload step boundary extends into the following workflow step")
    if 'foreach ($folder in @("scripts", "lib", "app", "components", "electron", "tests"' not in text:
        raise SystemExit("Windows lifecycle artifact does not preserve the desktop app, UI and test sources")

    kba_pipeline_paths = (
        ".github/workflows/build-kba-de-vag-stock-research-pack.yml",
        ".github/workflows/probe-kba-open-data.yml",
        "scripts/build_kba_de_vag_stock_research_pack.py",
        "scripts/probe_kba_open_data.py",
        "scripts/integrate-kba-de-vag-stock-research-pack.cjs",
        "scripts/apply-kba-de-vag-research-verification-run1.cjs",
        "tests/test_kba_de_vag_stock_research_pack.py",
        "tests/test_kba_open_data_probe.py",
        "tests/kba-pack-integration-contract.test.cjs",
    )
    missing_kba_pipeline_paths = [marker for marker in kba_pipeline_paths if text.count(marker) < 2]
    if missing_kba_pipeline_paths:
        raise SystemExit(f"KBA pack code/data changes must trigger both push and pull-request validation: {missing_kba_pipeline_paths}")
    kba_pipeline_steps = (
        "python -m py_compile scripts/probe_kba_open_data.py scripts/build_kba_de_vag_stock_research_pack.py",
        'python -m unittest discover -s tests -p "test_kba_de_vag_stock_research_pack.py" -v',
        "node --test tests/kba-pack-integration-contract.test.cjs",
        "Resolve latest successful KBA DE VAG stock research pack run",
        "Download verified KBA DE VAG stock SQLite research pack",
        "node scripts/integrate-kba-de-vag-stock-research-pack.cjs",
        "node scripts/apply-kba-de-vag-research-verification-run1.cjs",
        "npm run verify:kba-de-stock-research",
        "kba-de-vag-stock-research/kba-de-vag-stock-research.sqlite",
        "kba-de-vag-stock-research/desktop-integration-report.json",
        "kba_de_vag_stock=run",
        "aggregate_stock_observation",
        "research_pack_ingested=true",
        "product_database_ingested=false",
    )
    missing_kba_pipeline_steps = [marker for marker in kba_pipeline_steps if marker not in text]
    if missing_kba_pipeline_steps:
        raise SystemExit(f"KBA pack integration/NSIS verification pipeline is incomplete: {missing_kba_pipeline_steps}")
    kba_integrate_marker = "      - name: Integrate KBA DE VAG aggregate-stock pack into offline desktop"
    desktop_tests_marker = "      - name: Run desktop, local core and research tests"
    installer_build_marker = "      - name: Build first Windows x64 NSIS installer"
    if not (text.index(kba_integrate_marker) < text.index(desktop_tests_marker) < text.index(installer_build_marker)):
        raise SystemExit("KBA pack must be integrated and verified before desktop tests and NSIS packaging")
    cardir_pipeline_paths = (
        ".github/workflows/build-cardir-vag-open-data-pack.yml",
        "data/source-manifests/cardir-vag-owner-manual-facts-cc-by-4.0.json",
        "docs/research/CARDIR_CC_BY_VAG_OWNER_MANUAL_FACTS_REVIEW_2026-11-07.md",
        "scripts/build_cardir_vag_open_data_pack.py",
        "scripts/integrate-cardir-vag-owner-manual-facts.cjs",
        "tests/test_cardir_vag_open_data_pack.py",
        "tests/test_cardir_vag_open_data_source_rights.py",
        "desktop/cardir-vag-reference-facts-db.cjs",
        "desktop/scripts/verify-cardir-vag-open-data-pack.cjs",
        "desktop/tests/cardir-vag-reference-facts-db.test.cjs",
        "desktop/tests/cardir-vag-reference-facts-ui-contract.test.cjs",
    )
    missing_cardir_pipeline_paths = [marker for marker in cardir_pipeline_paths if text.count(marker) < 2]
    if missing_cardir_pipeline_paths:
        raise SystemExit(f"CarDir source and desktop integration changes must trigger both push and pull-request validation: {missing_cardir_pipeline_paths}")
    cardir_pipeline_steps = (
        "python -m py_compile scripts/build_cardir_vag_open_data_pack.py",
        'python -m unittest discover -s tests -p "test_cardir_vag_open_data_pack.py" -v',
        "python tests/test_cardir_vag_open_data_source_rights.py",
        "node --check scripts/integrate-cardir-vag-owner-manual-facts.cjs",
        "Resolve pinned CarDir VAG owner-manual facts pack from source register",
        "Download verified CarDir VAG owner-manual facts SQLite research pack",
        "node scripts/integrate-cardir-vag-owner-manual-facts.cjs",
        "node --test desktop-source/tests/cardir-vag-reference-facts-db.test.cjs desktop-source/tests/cardir-vag-reference-facts-ui-contract.test.cjs",
        "node desktop-source/scripts/verify-cardir-vag-open-data-pack.cjs",
        "cardir_vag_owner_manual_facts=run",
        "facts=948; models=26; brands=5; parameters=19; market=UNKNOWN; research_only=true; production_import=false; exact_engine_gearbox_pair=false; ru_eaeu_applicability=false",
        "cardir_database_sha256",
        "cardir_source_snapshot_sha256",
        "cardir_vag_fact_count",
    )
    missing_cardir_pipeline_steps = [marker for marker in cardir_pipeline_steps if marker not in text]
    if missing_cardir_pipeline_steps:
        raise SystemExit(f"CarDir pack integration/NSIS verification pipeline is incomplete: {missing_cardir_pipeline_steps}")
    cardir_script = ROOT / "scripts" / "integrate-cardir-vag-owner-manual-facts.cjs"
    cardir_script_text = cardir_script.read_text(encoding="utf-8")
    for required in ("snapshot.source_row_count === 44272", "snapshot.vag_row_count === 948", "sourceFile.source_row_count === 44272", "sourceFile.filtered_vag_row_count === 948", "counts.vagFacts === 948 && counts.vagBrands === 5 && counts.vagModels === 26 && counts.parameterKeys === 19"):
        if required not in cardir_script_text:
            raise SystemExit(f"CarDir integration script is not pinned to the reviewed source snapshot: {required}")
    cardir_module = ROOT / "desktop" / "cardir-vag-reference-facts-db.cjs"
    if not cardir_module.is_file() or "pack.counts.vag_facts === 948 && pack.counts.vag_models === 26 && pack.counts.vag_brands === 5" not in cardir_module.read_text(encoding="utf-8"):
        raise SystemExit("CarDir desktop database module is missing or has stale snapshot counts")
    cardir_verifier = ROOT / "desktop" / "scripts" / "verify-cardir-vag-open-data-pack.cjs"
    if not cardir_verifier.is_file() or 'require("../lib/cardir-vag-reference-facts-db.cjs")' not in cardir_verifier.read_text(encoding="utf-8"):
        raise SystemExit("CarDir verifier must resolve the database module from the staged scripts directory")
    cardir_integrate_marker = "      - name: Integrate CarDir VAG reference facts into offline desktop"
    if not (text.index(kba_integrate_marker) < text.index(cardir_integrate_marker) < text.index(desktop_tests_marker) < text.index(installer_build_marker)):
        raise SystemExit("CarDir pack must be integrated and verified after KBA and before desktop tests and NSIS packaging")
    if "cardir_database_sha256=$($cardirSummary.databaseSha256)" not in text or "cardir_vag_owner_manual_facts_database_sha256 = $cardirDatabaseHash" not in text:
        raise SystemExit("Packaged CarDir database and snapshot hashes must be retained in package verification and build metadata")

    metadata_marker = "      - name: Write build metadata"
    if metadata_marker not in text:
        raise SystemExit("Windows build metadata step is missing")
    metadata_step = text.split(metadata_marker, 1)[1].split("\n      - name:", 1)[0]
    expected_oem_schema_path = '$oemDtcIndexSchemaPath = "desktop-source/data/schemas/oem-dtc-index.schema.json"'
    if expected_oem_schema_path not in metadata_step:
        raise SystemExit("OEM DTC schema SHA-256 must be computed from the staged desktop source tree")
    if '$oemDtcIndexSchemaPath = "data/schemas/oem-dtc-index.schema.json"' in metadata_step:
        raise SystemExit("OEM DTC schema hash path incorrectly points to the repository root")
    if 'if (-not $oemDtcIndexSchemaHash) { throw "OEM DTC index schema is missing from the staged desktop source." }' not in metadata_step:
        raise SystemExit("Windows metadata generation must fail closed when the OEM DTC schema is absent")
    if "Upload standalone build metadata for independent installer hash verification" in metadata_step:
        raise SystemExit("Build metadata step boundary extends into the following workflow step")

    run76_path = ".github/patches/desktop-source-run76/**"
    if text.count(run76_path) < 2:
        raise SystemExit("Run76 source patch must trigger both push and pull-request Windows validation")
    run76_dir = ROOT / ".github" / "patches" / "desktop-source-run76"
    run76_parts = sorted(run76_dir.glob("part-*.b64"))
    if len(run76_parts) != 4:
        raise SystemExit(f"Run76 source patch must have four immutable chunks, found {len(run76_parts)}")
    run76_encoded = "".join(part.read_text(encoding="ascii").strip() for part in run76_parts)
    if len(run76_encoded) != 6088 or hashlib.sha256(run76_encoded.encode("ascii")).hexdigest() != "5279408a9793c3c09dc941bae651961348b9a86d703f31a0dbf6a2f89e67d0be":
        raise SystemExit("Run76 source patch base64 length or SHA-256 is invalid")
    try:
        run76_compressed = base64.b64decode(run76_encoded, validate=True)
    except Exception as error:
        raise SystemExit(f"Run76 source patch base64 cannot be decoded: {error}") from error
    if hashlib.sha256(run76_compressed).hexdigest() != "ad757edb4ec08c990b27593fe771b2c37565e07c521ed5b89a90c41386adeac3":
        raise SystemExit("Run76 Brotli patch SHA-256 is invalid")
    run76_marker = '$patchPartsDir76 = Join-Path $env:GITHUB_WORKSPACE ".github/patches/desktop-source-run76"'
    if run76_marker not in text:
        raise SystemExit("Windows workflow does not apply the run76 exact vehicle-identity patch")
    run76_required = (
        '$parts76.Count -ne 4',
        '$encoded76.Length -ne 6088',
        '$encodedHash76 -ne "5279408a9793c3c09dc941bae651961348b9a86d703f31a0dbf6a2f89e67d0be"',
        '$compressedHash76 -ne "ad757edb4ec08c990b27593fe771b2c37565e07c521ed5b89a90c41386adeac3"',
        '$patchHash76 -ne "f90613c8baa29c3197e2af2bf73523efd4d7956e90e185820d8d841a75500017"',
        'git apply --check --unsafe-paths --directory=desktop-source $patchPath76',
        'vehicle_identity_match_requires_generation_market_year=true',
        'ambiguous_configuration_blocks_lookup=true',
    )
    missing_run76 = [marker for marker in run76_required if marker not in text]
    if missing_run76:
        raise SystemExit(f"Run76 exact vehicle-identity guard patch contract is incomplete: {missing_run76}")
    run76_index = text.index(run76_marker)
    run75_index = text.index("node apply-local-core-test-cleanup-run75.cjs")
    desktop_tests_index = text.index("      - name: Run desktop, local core and research tests")
    installer_index = text.index("      - name: Build first Windows x64 NSIS installer")
    if not (run75_index < run76_index < desktop_tests_index < installer_index):
        raise SystemExit("Run76 identity guard must apply after run75 cleanup and before desktop tests and NSIS packaging")

    ui_guard_script = ROOT / "apply-vehicle-config-ui-guard-run77.cjs"
    if not ui_guard_script.is_file():
        raise SystemExit("Run77 exact-configuration UI guard patch script is missing")
    ui_guard_text = ui_guard_script.read_text(encoding="utf-8")
    ui_guard_required = (
        "hasRequiredVehicleIdentity = Boolean",
        "selectedVehicle.generation_name?.trim()",
        'selectedVehicle.market_scope !== "UNKNOWN"',
        "Number.isInteger(selectedVehicle.model_year)",
        "selectedVehicle.engine_code_declared?.trim()",
        "selectedVehicle.transmission_code_declared?.trim()",
        "matchingConfigurations.length === 1",
        "matchingConfigurations[0]?.id !== configurationId",
    )
    missing_ui_guard = [item for item in ui_guard_required if item not in ui_guard_text]
    if missing_ui_guard:
        raise SystemExit(f"Run77 UI guard does not enforce complete exact vehicle identity: {missing_ui_guard}")
    ui_guard_apply_marker = "node apply-vehicle-config-ui-guard-run77.cjs --desktop-root desktop-source"
    ui_guard_test_marker = "node --test desktop-source/tests/local-offline-workspace.test.cjs"
    if ui_guard_apply_marker not in text or ui_guard_test_marker not in text:
        raise SystemExit("Windows workflow must apply and test the run77 exact-configuration UI guard")
    run76_apply_marker = "git apply --unsafe-paths --directory=desktop-source $patchPath76"
    if not (text.index(run76_apply_marker) < text.index(ui_guard_apply_marker) < text.index(ui_guard_test_marker) < text.index(desktop_tests_marker)):
        raise SystemExit("Run77 UI guard must apply after the run76 backend guard and pass its UI tests before the full desktop suite")
    metadata_step = text.split("      - name: Write build metadata", 1)[1].split("\n      - name:", 1)[0]
    if "vehicle_config_ui_guard_patch_sha256 = $uiGuardPatchHash;" not in metadata_step or 'Get-FileHash -LiteralPath "apply-vehicle-config-ui-guard-run77.cjs"' not in metadata_step:
        raise SystemExit("Windows build metadata must record the exact run77 UI guard patch SHA-256")
    if text.count("apply-vehicle-config-ui-guard-run77.cjs") < 4:
        raise SystemExit("Run77 UI guard script and its logs must be retained in Windows CI evidence artifacts")

    cardir_resolver_marker = "      - name: Resolve pinned CarDir VAG owner-manual facts pack from source register"
    cardir_resolver_step = text.split(cardir_resolver_marker, 1)[1].split("\n      - name: Download verified CarDir", 1)[0]
    for required in ("ConvertFrom-Json -AsHashtable", "$pack.artifact_run_id", "$pack.artifact_id", "$pack.artifact_sha256", "$pack.source_manifest_sha256", "$pack.source_snapshot_sha256", "Get-FileHash"):
        if required not in cardir_resolver_step:
            raise SystemExit(f"CarDir resolver must use immutable source-register artifact pins: {required}")
    if "$expectedHeadSha" in cardir_resolver_step:
        raise SystemExit("CarDir pack resolution must be pinned to source-manifest and snapshot hashes, not a transient repository commit")
    build_cardir_workflow = (ROOT / ".github" / "workflows" / "build-cardir-vag-open-data-pack.yml").read_text(encoding="utf-8")
    if "data/source-manifests/vag-factory-source-register.json" in build_cardir_workflow:
        raise SystemExit("CarDir pack rebuild must not be triggered by source-register artifact-pin updates; that creates a provenance rebuild loop")
    ownerspecs_marker = "      - name: Resolve pinned OwnerSpecs VAG CC BY-SA research pack"
    if ownerspecs_marker not in text:
        raise SystemExit("Windows workflow is missing the pinned OwnerSpecs research-pack resolver")
    ownerspecs_step = text.split(ownerspecs_marker, 1)[1].split("\n      - name:", 1)[0]
    if ownerspecs_step.count("ConvertFrom-Json -AsHashtable") != 1 or "ConvertFrom-Json -AsHashtable -AsHashtable" in ownerspecs_step:
        raise SystemExit("OwnerSpecs resolver must use exactly one -AsHashtable to preserve case-sensitive source-register keys")
    owner_hash_bindings = (
        '@{ path=(Join-Path $ownerResearchRoot $ownerEntry.source_file); hash=$ownerEntry.source_file_sha256 }',
        '@{ path=(Join-Path $ownerResearchRoot $ownerEntry.source_snapshot_file); hash=$ownerEntry.source_snapshot_file_sha256 }',
        '@{ path=(Join-Path $ownerResearchRoot $ownerEntry.acquisition_snapshot_file); hash=$ownerEntry.acquisition_snapshot_sha256 }',
    )
    missing_owner_hash_bindings = [marker for marker in owner_hash_bindings if marker not in step]
    if missing_owner_hash_bindings or '$ownerEntry.source_snapshot_file); hash=$ownerEntry.source_snapshot_sha256' in step:
        raise SystemExit(f"OwnerSpecs lifecycle must hash the raw source, snapshot metadata and acquisition snapshot using their distinct digest fields: {missing_owner_hash_bindings}")
    rights_step_marker = "      - name: Validate offline data-pack tooling and rights boundaries"
    if rights_step_marker not in text:
        raise SystemExit("Windows workflow is missing the offline data-pack rights validation step")
    rights_step = text.split(rights_step_marker, 1)[1].split("\n      - name:", 1)[0]
    if '$PSNativeCommandUseErrorActionPreference = $true' not in rights_step:
        raise SystemExit("PowerShell rights-validation step must fail on every non-zero native command")
    rights_command_order = (
        "python tests/test_ownerspecs_source_rights.py",
        'if ($LASTEXITCODE -ne 0) { throw "OwnerSpecs CC BY-SA rights/applicability tests failed." }',
        "python tests/test_cardir_source_rights.py",
        'if ($LASTEXITCODE -ne 0) { throw "CarDir live snapshot multiset review failed." }',
    )
    rights_positions = [rights_step.find(marker) for marker in rights_command_order]
    if any(position < 0 for position in rights_positions) or rights_positions != sorted(rights_positions):
        raise SystemExit("OwnerSpecs and CarDir source-rights checks must each immediately follow their own test command")

    pull_request_trigger = text.split("  pull_request:", 1)[1].split("\njobs:", 1)[0]
    owner_paths = (
        "scripts/integrate-ownerspecs-vag-research.cjs",
        "tests/test_ownerspecs_source_rights.py",
        "tests/ownerspecs-pack-integration-contract.test.cjs",
        "data/source-manifests/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0.json",
        "desktop/ownerspecs-vag-research-db.cjs",
    )
    missing_owner_paths = [path for path in owner_paths if ('"' + path + '"') not in pull_request_trigger]
    if missing_owner_paths:
        raise SystemExit(f"Windows pull-request path filter must rerun for OwnerSpecs integration changes: {missing_owner_paths}")

    mechanicdb_register = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
    mechanicdb_entries = [entry for entry in mechanicdb_register["sources"] if entry.get("source_id") == "mechanicdb-vag-dtc-candidates-odbl"]
    if len(mechanicdb_entries) != 1:
        raise SystemExit("MechanicDB candidate source must have exactly one central register entry")
    mechanicdb = mechanicdb_entries[0]
    mechanicdb_expected = {
        "research_pack_run_id": 41622526550,
        "research_pack_run_number": 8,
        "research_pack_artifact_id": 13223942420,
        "research_pack_artifact_name": "mechanicdb-audi-vw-dtc-candidates-odbl-research",
        "research_pack_source_commit": "05a58d9e800dc9d725f3cc254857f68c32cf59c6",
        "artifact_sha256": "f294bf4ebe6384b2ad6a586244ba0c49011fb441c691006c460d8a070744a5d6",
        "source_snapshot_sha256": "f123b251659b45f4acf64071329dec6dc3a4ba1c8b2f827ff1ad3b45e28e0c94",
        "source_csv_sha256": "796fa2b18bdbff311f15eb4943b68adbf7241e564ce8eff32023a2d297694bff",
        "display_status": "candidate_reference_visible_separate_namespace",
    }
    for key, value in mechanicdb_expected.items():
        if mechanicdb.get(key) != value:
            raise SystemExit(f"MechanicDB source-register pin mismatch for {key}")
    if mechanicdb.get("research_pack_ingested") is not True or mechanicdb.get("data_ingested") is not False or mechanicdb.get("product_database_ingested") is not False:
        raise SystemExit("MechanicDB must remain an isolated research pack and never enter the production catalog")
    if mechanicdb.get("counts", {}).get("generic_sae_iso_rows") != 0 or mechanicdb.get("counts", {}).get("manufacturer_controlled_candidates") != 2:
        raise SystemExit("MechanicDB candidate pack must contain only the two make-labelled candidates and zero generic DTC rows")
    if mechanicdb.get("display_policy", {}).get("diagnostic_execution_allowed") is not False or mechanicdb.get("display_policy", {}).get("vag_oem_confirmation") is not False:
        raise SystemExit("MechanicDB candidate display must remain non-actionable and not OEM-confirmed")

    mechanicdb_resolver_marker = "      - name: Verify pinned MechanicDB Audi/VW candidate artifact"
    if mechanicdb_resolver_marker not in text:
        raise SystemExit("Windows workflow is missing the MechanicDB artifact ID/digest resolver")
    mechanicdb_resolver = text.split(mechanicdb_resolver_marker, 1)[1].split("\\n      - name: Download MechanicDB candidate pack", 1)[0]
    for required in ("ConvertFrom-Json -AsHashtable", "research_pack_run_id", "research_pack_artifact_id", "artifact.digest", "artifact_sha256", "research_pack_source_commit"):
        if required not in mechanicdb_resolver:
            raise SystemExit(f"MechanicDB resolver is missing a pinned artifact/provenance check: {required}")
    mechanicdb_download = text.split("      - name: Download MechanicDB candidate pack", 1)[1].split("\\n      - name:", 1)[0]
    if "run-id: \${{ steps.mechanicdb-pack.outputs.run_id }}" not in mechanicdb_download:
        raise SystemExit("MechanicDB download must use the verified source-register run ID, not an unverified hard-coded run")

    print("Windows desktop workflow contract: lifecycle paths, source-rights register and Wikidata snapshot pins are valid.")

if __name__ == "__main__":
    main()
