# Windows dependency lock refresh — 2026-11-08

The Windows build job generated a fresh package lock using Node 22.16.0 and npm 10.9.2 after applying the repository's pinned dependency overrides. The generated lock was preserved in the run 702 diagnostic artifact and its SHA-256 was independently recomputed from the artifact bytes:

`8f6b952801b8beb7c01f9330a06a5ab929c77c9db59a06b194b1532685bc6667`

The previous repository pin (`a1c99e...`) did not match the generated lock, so the build stopped before installation and audit. The pin is updated to the observed lock hash. The next Windows CI run must still complete clean installation, installed-tree/lock equality, production and full dependency audits, build and installer lifecycle before this lock refresh is considered fully validated.

The generated lock reported:
- top-level `minimatch@11.0.1`;
- nested `minimatch@3.1.5` and `5.1.9` entries, which are below the affected major-version range checked by the workflow;
- patched `caniuse-lite@1.0.30001822`;
- `electron-to-chromium@1.5.478`.

No package was installed into a user environment. This is a CI dependency lock pin only.
