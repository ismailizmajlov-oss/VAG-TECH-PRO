#!/usr/bin/env python3
"""Regression checks for the Windows Server 2022 lifecycle workflow script."""

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

    artifact_root = '$artifactRoot = Join-Path $env:RUNNER_TEMP "vag-tech-pro-run70-artifact/windows-lifecycle-staging"'
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

    print("Windows desktop workflow contract: lifecycle path initialization order is valid.")


if __name__ == "__main__":
    main()
