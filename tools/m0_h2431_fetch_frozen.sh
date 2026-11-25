#!/usr/bin/env bash
set -euo pipefail
PRODUCT=dadb01fcd816f07db51bb410ba04d2a60702a2f7
RUN=45566751681
ARCH="${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}"
case "$ARCH" in
 x86_64) ID=14999404352;;
 aarch64) ID=15000193682;;
 *) exit 2;;
esac
git diff --exit-code "$PRODUCT" "$GITHUB_SHA" -- crates r0 Cargo.toml Cargo.lock tools/m0_plan029_linux_dual_native_build.sh tools/m0_linux_glibc231_build.sh
mkdir -p h2431-download linux-plan029-public-bundle
gh run download "$RUN" --repo "$GITHUB_REPOSITORY" --name "h2430-product-$ARCH-$PRODUCT" --dir h2431-download
tar -xzf h2431-download/h2430-product.tgz -C linux-plan029-public-bundle
(cd linux-plan029-public-bundle && sha256sum -c SHA256SUMS)
python3 - "$PRODUCT" "$ARCH" "$RUN" "$ID" <<'PY'
import json,pathlib,sys
m=json.loads(pathlib.Path("linux-plan029-public-bundle/manifest.json").read_text())
assert m["source_sha"]==sys.argv[1] and m["architecture"]==sys.argv[2]
pathlib.Path("h2431-build-identity.json").write_text(json.dumps({"manifest":m,"run":int(sys.argv[3]),"artifact_id":int(sys.argv[4])},indent=2)+"\n")
PY
