#!/usr/bin/env python3
"""Guard the native Windows client lifecycle against stale upstream workflow names."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_WORKFLOW = ROOT / ".github" / "workflows" / "windows-desktop-ci-run71.yml"
NATIVE_WORKFLOW = ROOT / ".github" / "workflows" / "windows-10-11-native-lifecycle.yml"


def main() -> None:
    desktop_text = DESKTOP_WORKFLOW.read_text(encoding="utf-8")
    native_text = NATIVE_WORKFLOW.read_text(encoding="utf-8")

    desktop_name = re.search(r"(?m)^name:[ \t]*(.+?)[ \t]*$", desktop_text)
    trigger = re.search(
        r"(?m)^  workflow_run:[ \t]*\n    workflows:[ \t]*\n(?P<items>(?:^      - .*\n)+)",
        native_text,
    )
    if not desktop_name or not trigger:
        raise SystemExit("Native Windows 10/11 workflow must listen to the desktop workflow_run event")

    upstream_names = re.findall(r"(?m)^      - (.+?)[ \t]*$", trigger.group("items"))
    if upstream_names != [desktop_name.group(1)]:
        raise SystemExit(
            "Native Windows 10/11 trigger must name exactly the current desktop workflow; "
            f"desktop={desktop_name.group(1)!r}, native={upstream_names!r}"
        )

    status_workflow = re.search(
        r'(?m)^[ \t]*upstream_workflow[ \t]*=[ \t]*"([^"]+)"',
        native_text,
    )
    if not status_workflow or status_workflow.group(1) != desktop_name.group(1):
        raise SystemExit("Native Windows status recorder must identify the exact current desktop workflow")

    if not re.search(r"(?m)^    branches:[ \t]*\n      - main[ \t]*$", native_text):
        raise SystemExit("Native Windows lifecycle must only consume successful main-branch builds")
    if not re.search(r"(?m)^    types:[ \t]*\n      - completed[ \t]*$", native_text):
        raise SystemExit("Native Windows lifecycle must run after the upstream build completes")

    required_gate = "vars.VAG_TECH_PRO_WIN10_11_RUNNER_AVAILABLE == 'true'"
    if required_gate not in native_text:
        raise SystemExit("Native Windows lifecycle must remain owner-gated")
    for label in ("self-hosted", "windows", "x64", "vag-tech-pro-win10-11"):
        if label not in native_text:
            raise SystemExit(f"Native Windows lifecycle runner label is missing: {label}")

    print("Native Windows 10/11 workflow binding valid: " + desktop_name.group(1))


if __name__ == "__main__":
    main()
