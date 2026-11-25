#!/usr/bin/env bash
set -euo pipefail
PRODUCT=3971bbca8fd5e2d40497be313251df64e186136e
RUN=45570805865
ARCH="${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}"
case "$ARCH" in
 x86_64) ID=15001828842;;
 aarch64) ID=15002087217;;
 *) exit 2;;
esac
git diff --exit-code "$PRODUCT" "$GITHUB_SHA" -- crates r0 Cargo.toml Cargo.lock tools/m0_plan029_linux_dual_native_build.sh tools/m0_linux_glibc231_build.sh
mkdir -p h2434-download linux-plan029-public-bundle
gh run download "$RUN" --repo "$GITHUB_REPOSITORY" --name "h2433-product-$ARCH-$PRODUCT" --dir h2434-download
tar -xzf h2434-download/h2433-product.tgz -C linux-plan029-public-bundle
(cd linux-plan029-public-bundle && sha256sum -c SHA256SUMS)
python3 - "$PRODUCT" "$ARCH" "$RUN" "$ID" <<'PY'
import json,pathlib,sys
m=json.loads(pathlib.Path("linux-plan029-public-bundle/manifest.json").read_text())
assert m["source_sha"]==sys.argv[1] and m["architecture"]==sys.argv[2]
pathlib.Path("h2434-build-identity.json").write_text(json.dumps({"manifest":m,"run":int(sys.argv[3]),"artifact_id":int(sys.argv[4])},indent=2)+"\n")
PY
