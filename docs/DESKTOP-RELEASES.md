# Desktop builds and signing

Tracking and remaining acceptance: [#1081](https://github.com/superche/openmatlab/issues/1081).
Design: [ISSUE-1081](design/ISSUE-1081-desktop-distributions.md).

## Get test builds

Open Actions → Desktop distributions → a successful run → Artifacts.
`unsigned-windows-x64` contains a per-user `.exe` installer;
`unsigned-macos-arm64` contains a `.dmg`. Both include checksums.
These builds require no installed Python. They are development builds without
public-trust signing; macOS PyInstaller's ad-hoc signature is not Developer ID.
For terminal use, `openmatlab-cli.exe` is beside the Windows launcher; on macOS
use `OpenMATLAB.app/Contents/MacOS/openmatlab-cli`.

Local native build (Python 3.12, matching target architecture):

```sh
python -m pip install -e '.[numpy,plot]' PyYAML -r packaging/requirements.txt
python -m PyInstaller --noconfirm --clean packaging/openmatlab.spec
# macOS
python packaging/smoke.py dist/OpenMATLAB.app/Contents/MacOS --arch arm64
# Windows
python packaging/smoke.py dist/OpenMATLAB --arch x64
```

## Apple personal developer account

Paid Apple Developer Program membership is needed for Developer ID signing and
notarization, not for building or local testing. Personal membership suffices;
App Store distribution and an enterprise account are unnecessary.

1. Sign into [Apple Certificates](https://developer.apple.com/account/resources/certificates/list).
   Create **Developer ID Application**, not Apple Development or Apple Distribution.
   Generate the CSR with Keychain Access on your Mac if requested.
2. Install the downloaded certificate in Keychain Access. Under **My Certificates**,
   expand it and confirm its private key exists. Export certificate plus private key
   as `.p12`, protected by a strong export password. Keep this file outside the repo.
3. In [GitHub environments](https://github.com/superche/openmatlab/settings/environments),
   create `release`; restrict deployments to main and protected `v*` tags.
   Add these environment secrets (never send values in chat):

   | Secret | Value |
   | --- | --- |
   | `APPLE_CERTIFICATE_BASE64` | `base64 -i /absolute/path/DeveloperID.p12` output |
   | `APPLE_CERTIFICATE_PASSWORD` | The p12 export password |
   | `APPLE_ID` | Apple account email |
   | `APPLE_APP_PASSWORD` | App-specific password from account.apple.com, not login password |

4. Add environment variables:

   | Variable | Value |
   | --- | --- |
   | `APPLE_TEAM_ID` | Team ID from Apple membership details |
   | `APPLE_SIGNING_IDENTITY` | Exact `Developer ID Application: Your Name (TEAMID)` identity |

   Find the identity locally with `security find-identity -v -p codesigning`.
   For this DMG route no Developer ID Installer certificate is needed.
5. Once the workflow is merged, run Desktop distributions on **main**, enable
   `sign_macos`. Download `signed-macos-arm64`. Windows remains an unsigned build
   in that run. The workflow signs nested binaries/app, notarizes and staples the
   app, creates and signs the DMG, then notarizes/staples the DMG.
6. Download using a browser onto a clean Apple Silicon Mac, install by dragging to
   Applications, open normally, calculate a matrix and draw a figure. Record the
   result in #1081. Automated `codesign`, `stapler`, and `spctl` checks are additional
   evidence, not a substitute for this downloaded-app check.

[Apple Developer ID](https://developer.apple.com/developer-id/) ·
[GitHub certificate handling](https://docs.github.com/en/actions/how-tos/deploy/deploy-to-third-party-platforms/sign-xcode-applications)

## Windows without an existing certificate

Apply to [SignPath Foundation](https://signpath.org/) for open-source signing.
It requires project approval and service configuration; no approval has yet been
obtained for OpenMATLAB. Foundation signing uses the Foundation as certificate
publisher and requires an already available application build, project reputation,
a published signing policy/roles, and manual approval for each release. Prepare
these in #1081 after the unsigned build is accepted; do not claim sponsorship before
approval. See [eligibility and policy](https://signpath.org/terms). Do not buy a USB-token certificate for a hosted runner.

After approval, connect this GitHub repository using SignPath's trusted build
integration, restrict production signing to protected tags, and configure:

- Secret `SIGNPATH_API_TOKEN` in `release`.
- Variables `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`,
  `SIGNPATH_SIGNING_POLICY_SLUG` (production public-trust policy with timestamps).
- Artifact configuration `windows-app`: uploaded directory archive, preserve
  contents/layout and Authenticode-sign `OpenMATLAB.exe` and `openmatlab-cli.exe`.
- Artifact configuration `windows-installer`: uploaded archive containing the
  single `OpenMATLAB-*-windows-x64-setup.exe`, Authenticode-sign that installer.

The workflow signs the application before embedding it in the installer, then
signs the installer. Both stages require valid signatures and timestamp
certificates. Keep vendor runtime files intact. SignPath policy approvals may
need operator action during a release. Test the complete flow before claiming
Windows release signing works.

[SignPath GitHub integration](https://docs.signpath.io/trusted-build-systems/github).
If enrollment is declined, select an eligible commercial cloud/HSM provider in
#1081; do not silently substitute self-signing.

## Release

Update `pyproject.toml` and `src/openmatlab/__init__.py` versions through a PR.
After required tests, native builds and signing setup are accepted, create a
protected `v<version>` tag on main. Desktop distributions tests the tagged source,
runs the full corpus regression gate, builds/signs both platforms and publishes
one Release with both installers and checksums. Existing nightly regressions
must be diagnosed; do not edit baselines to obtain a release. A failure leaves
workflow evidence/artifacts but publishes no Release. Existing Release assets
are not overwritten. No version tag is created by this change.

Developer-oriented CLI commands (`test`, `defects`, subprocess corpus `run`) are
not part of standalone acceptance; they rely on a development checkout/tools.
Broader frozen CLI support remains tracked by #1081.
