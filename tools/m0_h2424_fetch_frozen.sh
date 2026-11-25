#!/usr/bin/env bash
# Pin the already measured H2423 product; new harness only.
set -euo pipefail
PRODUCT=559f2093857919c6293ee6f85622b55f198251fc
BUILD_RUN=45556602991
ARTIFACT=14995813926
git cat-file -e "$PRODUCT^{commit}"
git diff --exit-code "$PRODUCT" "$GITHUB_SHA" -- crates r0 Cargo.toml Cargo.lock tools/m0_plan029_linux_dual_native_build.sh tools/m0_linux_glibc231_build.sh
mkdir -p h2424-download linux-plan029-public-bundle
gh run download "$BUILD_RUN" --repo "$GITHUB_REPOSITORY" --name "h2423-product-x86_64-$PRODUCT" --dir h2424-download
tar -xzf h2424-download/h2423-product.tgz -C linux-plan029-public-bundle
(cd linux-plan029-public-bundle && sha256sum -c SHA256SUMS)
python3 - "$PRODUCT" "$BUILD_RUN" "$ARTIFACT" <<'PY'
import json,pathlib,sys
p=pathlib.Path("linux-plan029-public-bundle")
d=json.loads((p/"manifest.json").read_text())
assert d["source_sha"]==sys.argv[1] and d["architecture"]=="x86_64"
pathlib.Path("h2423-build-identity.json").write_text(json.dumps({"build_run":int(sys.argv[2]),"artifact_id":int(sys.argv[3]),"manifest":d},indent=2)+"\n")
PY
