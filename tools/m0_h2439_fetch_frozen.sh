#!/usr/bin/env bash
set -euo pipefail
PRODUCT=5e1b68331a4b666287ee28219f30a6b7c70df0dd
RUN=45585194668
ARCH="${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}"
case "$ARCH" in
 aarch64) ID=15008292420;;
 x86_64) ID=15007774236;;
 *) exit 2;;
esac
git diff --exit-code "$PRODUCT" "$GITHUB_SHA" -- crates r0 Cargo.toml Cargo.lock tools/m0_plan029_linux_dual_native_build.sh tools/m0_linux_glibc231_build.sh
mkdir -p h2439-download linux-plan029-public-bundle h2439-out
gh run download "$RUN" --repo "$GITHUB_REPOSITORY" --name "h2437-product-$ARCH-$PRODUCT" --dir h2439-download
tar -xzf h2439-download/h2437-product.tgz -C linux-plan029-public-bundle
(cd linux-plan029-public-bundle && sha256sum -c SHA256SUMS)
python3 - "$PRODUCT" "$ARCH" "$RUN" "$ID" <<'PY'
import json,pathlib,sys
m=json.loads(pathlib.Path("linux-plan029-public-bundle/manifest.json").read_text())
assert m["source_sha"]==sys.argv[1] and m["architecture"]==sys.argv[2]
pathlib.Path("h2439-out/build-identity.json").write_text(json.dumps({"manifest":m,"run":int(sys.argv[3]),"artifact_id":int(sys.argv[4])},indent=2)+"\n")
PY
