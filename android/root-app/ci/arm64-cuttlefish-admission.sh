#!/usr/bin/env bash
# Preflight on ACTUAL ARM64 Linux host; does NOT run Android or claim P2/P3.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
p=out/android-a3-guest/android-root-app
test "$(cat "$p/SOURCE")" = "$GITHUB_SHA"
(cd "$p" && sha256sum -c SHA256SUMS)
test -s "$p/wbd-root-arm64-debug.apk"
mkdir -p out/android-a3-guest-admission
WBD_ARCH="$(uname -m)"
WBD_KERNEL="$(uname -r)"
WBD_KVM=NOT_AVAILABLE
if test -c /dev/kvm && test -r /dev/kvm && test -w /dev/kvm; then WBD_KVM=AVAILABLE;fi
export WBD_ARCH WBD_KERNEL WBD_KVM
python3 - <<'PY'
import json,os,pathlib
arch=os.environ["WBD_ARCH"];kvm=os.environ["WBD_KVM"]
reason=("HOST_IS_NOT_AARCH64" if arch!="aarch64" else
        "KVM_NOT_ACCESSIBLE" if kvm!="AVAILABLE" else
        "PINNED_CUTTLEFISH_IMAGE_AND_HOST_TOOLS_NOT_PROVISIONED")
receipt={
 "schema":"wbd-android-arm64-cuttlefish-host-admission/v1",
 "source":os.environ["GITHUB_SHA"],"host_arch":arch,
 "host_kernel":os.environ["WBD_KERNEL"],"host_kvm":kvm,
 "status":"ENV_BLOCKED","reason":reason,
 "guest_image":"NOT_PROVISIONED","android16_arm64_guest":"NOT_RUN",
 "signed_root_apk_install":"NOT_RUN","app_su_root":"NOT_RUN",
 "bionic_go_rust_runtime":"NOT_RUN","android_linux_e2e":"NOT_RUN",
 "adb_root_vs_ksu_equivalence":"NOT_PROVEN",
 "physical_final":"DEFERRED"}
p=pathlib.Path("out/android-a3-guest-admission/admission.json")
p.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("ANDROID_ARM64_KVM_HOST_ADMISSION_ONLY",reason,"arch",arch,"kvm",kvm)
PY
