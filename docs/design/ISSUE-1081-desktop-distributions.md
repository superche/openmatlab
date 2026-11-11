# Desktop distributions (#1081)

Tracking: https://github.com/superche/openmatlab/issues/1081

## Design

Keep the Python/Tkinter host. PyInstaller collects the existing CLI and a thin
Workbench launcher into one dependency directory. Native GitHub-hosted
`windows-2022` x64 and `macos-15` arm64 jobs produce an Inno Setup installer and a
DMG containing the app. Python, Tcl/Tk, NumPy, Matplotlib, YAML inventories and
package resources ship with the application. Corpus caches/datasets do not.

PR/main builds produce explicitly `unsigned` artifacts, including that suffix
in filenames. A manual main run can sign macOS independently while Windows
remains unsigned. Version tags require BOTH signing paths; missing credentials
fail the job rather than silently publishing unsigned software. Publication
needs both platform builds plus unit/BDD and full corpus gates at the tagged SHA.
Tags must match both Python version declarations and point to a main ancestor.

`packaging/smoke.py` inspects actual Mach-O/PE architecture and starts the frozen
CLI and GUI outside the checkout. It checks matrix assertions, bundled
inventories, a plot PNG, and Workbench startup/automatic close. This does not
replace manual downloaded-installer/Gatekeeper/SmartScreen acceptance on a clean
machine. Windows certificates do not guarantee immediate SmartScreen reputation.

## Signing boundaries

PR builds never reference a signing secret in executed steps. Signing runs use
the `release` GitHub environment. Configure its deployment branch/tag policy
for main and protected `v*` tags, and limit who may create those tags. Signing
identities belong to the publisher, not GitHub. macOS uses a temporary keychain
and cleans it on failure as well as success. SignPath holds the Windows key;
only its API token is stored in GitHub. Windows application and installer are
signed separately, then signatures/timestamps are verified before use.

## Scope and evidence

This is a partial delivery until #1081's signing and downloaded-app acceptance
criteria have real evidence. Apple personal membership is available per owner;
certificate setup is pending. Windows has no signing provider enrolled yet.
SignPath Foundation is the proposed open-source route; approval is external.
All remaining signing/onboarding/clean-machine acceptance work stays in #1081.
No existing corpus regression is waived by this packaging work.

Gherkin waiver: packaging infrastructure; acceptance is executable frozen-product
smoke plus release-policy unit tests, catalogued in `docs/test_catalog.yaml`.

Operations: [desktop releases](../DESKTOP-RELEASES.md).
