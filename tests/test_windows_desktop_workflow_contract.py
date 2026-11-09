#!/usr/bin/env python3
"""Regression checks for Windows packaging and pinned research-pack alignment."""

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
    status_workflow = re.search(r'(?m)^\s+upstream_workflow:\s*"([^"]+)"', native_text)
    if not status_workflow or status_workflow.group(1) != desktop_workflow_name.group(1):
        raise SystemExit("Native Windows status record must identify the exact upstream desktop workflow")
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

    patch_set_line = next((line for line in text.splitlines() if "patch_set = " in line), "")
    required_patch_set = (
        "run76-desktop-row-types-fix",
        "run77-lifecycle-session-output",
        "run78-rdw-ui-contract",
        "run79-typed-technical-payload-renderer",
        "run80-technical-payload-schema-validation",
        "run81-strict-dtc-oem-supersession-validation",
    )
    missing_patch_set = [marker for marker in required_patch_set if marker not in patch_set_line]
    if missing_patch_set:
        raise SystemExit(f"Windows build metadata patch_set omits applied desktop changes: {missing_patch_set}")

    print("Windows desktop workflow contract: lifecycle paths, source-rights register and Wikidata snapshot pins are valid.")


    rdw_step_marker = "      - name: Resolve latest successful RDW NL/EU research pack run"
    if rdw_step_marker not in text:
        raise SystemExit("Windows workflow is missing the current RDW pack resolver")
    rdw_step = text.split(rdw_step_marker, 1)[1].split("\n      - name:", 1)[0]
    if 'for ($attempt = 0; $attempt -lt 120 -and $run.status -ne "completed"; $attempt++)' not in rdw_step or "Start-Sleep -Seconds 20" not in rdw_step:
        raise SystemExit("RDW pack resolver must allow a 40-minute completion window for the measured acquisition duration")
    if "timeout-minutes: 90" not in text:
        raise SystemExit("Windows build job must leave headroom after the 40-minute RDW pack wait")

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

if __name__ == "__main__":
    main()
