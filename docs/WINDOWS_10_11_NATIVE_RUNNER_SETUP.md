# Native Windows 10/11 x64 release-gate runner

## Why this is a separate gate

The hosted Windows Server 2022 lifecycle job is useful evidence, but it is not a native Windows 10/11 client test. The native workflow deliberately refuses to treat Server as Windows 10/11. A release candidate remains blocked until this gate passes on an actual Windows 10 or Windows 11 x64 client OS.

## Owner-controlled setup

1. Provision an isolated Windows 10 22H2 x64 or Windows 11 x64 VM/device dedicated to this test. Do not use a production workstation or a machine containing customer vehicle data.
2. In the VAG-TECH-PRO repository's GitHub Actions settings, register a repository-level self-hosted runner for that machine.
3. Assign these exact labels: `self-hosted`, `windows`, `x64`, `vag-tech-pro-win10-11`.
4. Wait until the runner is online and idle. Confirm the OS is a client SKU (`Win32_OperatingSystem.ProductType = 1`), not Windows Server.
5. Set the repository Actions variable `VAG_TECH_PRO_WIN10_11_RUNNER_AVAILABLE=true` only after the runner is isolated, online and able to execute PowerShell. This variable is a gate, not a credential.
6. Let the native lifecycle workflow run after a successful Windows x64 desktop validation run. It downloads the two hashed NSIS installers and reviewed lifecycle contract from that exact upstream run.

## What the workflow verifies

- Actual Windows 10/11 client SKU, x64 architecture and OS build.
- SHA-256 of both initial and upgrade NSIS installers against upstream build metadata.
- Clean per-user installation of version 0.2.3.
- Launch with external network access blocked.
- Local SQLite integrity, backup and restore.
- In-place upgrade to version 0.2.4 without losing user data.
- Uninstall while preserving the user database and backup.

The workflow writes test data under `RUNNER_TEMP` and uses an isolated `APPDATA` directory. It does not require production deployment, payment keys, paid services, external accounts, or additional application secrets beyond the repository's standard Actions token used to download the build artifact.

## Operational safety

- Keep the runner dedicated to this repository and test job; do not run untrusted pull-request code on it.
- Do not add customer databases, real VINs, workshop credentials, OEM portal credentials or production secrets to the runner.
- Keep the runner patched and restrict local logon.
- After evidence is collected, set `VAG_TECH_PRO_WIN10_11_RUNNER_AVAILABLE=false` or take the runner offline until the next approved test window.
- Retain the uploaded `vag-tech-pro-windows-10-11-native-lifecycle` evidence artifact for audit.

## Current state

No Windows 10/11 self-hosted runner is provisioned or registered by the project workflow. Until the owner completes the steps above and the native job passes, the Windows 10/11 lifecycle requirement remains open. Windows Server 2022 success must not be represented as Windows 10/11 validation.
