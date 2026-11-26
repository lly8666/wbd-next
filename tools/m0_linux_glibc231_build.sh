#!/usr/bin/env bash
# Native ISA build environment only; the shipped ELF files run on the host.
set -euo pipefail
test "$(uname -m)" = "${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA:?}"
test "$(pwd)" = "${GITHUB_WORKSPACE:?}"
goroot="$(go env GOROOT)"
image="wbd-linux-glibc231:local"
docker build -t "$image" -f tools/linux-glibc231.Dockerfile tools
rc=0
docker run --rm \
  -e GITHUB_SHA -e GITHUB_WORKSPACE -e RUNNER_TEMP -e WBD_RUST_TOOLCHAIN \
  -e WBD_PLAN029_LINUX_EXPECTED_ARCH -e CGO_ENABLED=1 -e GOTOOLCHAIN=local \
  -e WBD_LINUX_GLIBC_BUILD_BASELINE=2.31-inner \
  -v "$GITHUB_WORKSPACE:$GITHUB_WORKSPACE" -v "$RUNNER_TEMP:$RUNNER_TEMP" \
  -v "$goroot:/opt/wbd-go:ro" -w "$GITHUB_WORKSPACE" "$image" \
  bash -c 'git config --global --add safe.directory "$GITHUB_WORKSPACE"; exec bash tools/m0_plan029_linux_dual_native_build.sh' || rc=$?
# Preserve original build helper outputs for its host-side consumers.
for p in legacy target linux-plan029-public-bundle "$RUNNER_TEMP/wbd-isa-l" "$RUNNER_TEMP/wbd-isal-plan029-$(uname -m)"; do
  if test -e "$p"; then sudo chown -R "$(id -u):$(id -g)" "$p"; fi
done
test "$rc" = 0
python3 - "$image" <<'PY'
import json,pathlib,subprocess,sys
p=pathlib.Path("linux-plan029-public-bundle/manifest.json")
m=json.loads(p.read_text())
m["build_container_image_id"]=subprocess.check_output(["docker","image","inspect","--format","{{.Id}}",sys.argv[1]],text=True).strip()
p.write_text(json.dumps(m,indent=2)+"\n")
PY
