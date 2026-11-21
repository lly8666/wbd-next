#!/usr/bin/env bash
# KSU 3.3.1 in one disposable Android16 AVD. Stock SDK ramdisk is NEVER modified.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
mkdir -p out/ksu out/native
export ANDROID_AVD_HOME="$GITHUB_WORKSPACE/out/ksu/avd-home"
mkdir -p "$ANDROID_AVD_HOME"
echo "ANDROID_AVD_HOME=$ANDROID_AVD_HOME" >>"$GITHUB_ENV"
test -c /dev/kvm || { echo "ENV_BLOCKED: missing /dev/kvm"; exit 2; }
sudo chmod a+rw /dev/kvm
sdkmanager="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
avdmanager="$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager"
test -x "$sdkmanager" && test -x "$avdmanager"
printf 'y\n' | "$sdkmanager" "system-images;android-36;google_apis_playstore;x86_64" >out/ksu/sdk-install.txt 2>&1 || { tail -n 70 out/ksu/sdk-install.txt; exit 2; }
image="$ANDROID_HOME/system-images/android-36/google_apis_playstore/x86_64"
test -s "$image/kernel-ranchu" && test -s "$image/ramdisk.img"
printf 'no\n' | "$avdmanager" create avd -n wbd_ksu36 -k "system-images;android-36;google_apis_playstore;x86_64" -p "$ANDROID_AVD_HOME/wbd_ksu36.avd" --force >out/ksu/avd-create.txt 2>&1
"$ANDROID_HOME/emulator/emulator" -list-avds >out/ksu/avd-list.txt
cat out/ksu/avd-list.txt
grep -qx wbd_ksu36 out/ksu/avd-list.txt || { echo "ENV_BLOCKED: AVD config was not registered"; find "$ANDROID_AVD_HOME" -maxdepth 2 -type f -print; exit 2; }
git clone --quiet https://github.com/leemikepop/avd-kernelsu-x86_64 out/ksu/helper
(cd out/ksu/helper && git checkout --quiet c6c6057d807976d3dee6dbe9197189654cbd1a2a)
echo c6c6057d807976d3dee6dbe9197189654cbd1a2a >out/ksu/helper-sha.txt
# The upstream helper explicitly reads GITHUB_TOKEN for authenticated GitHub Releases API.
# Hosted runner unauthenticated REST budget can be exhausted across concurrent jobs.
export GITHUB_TOKEN="$GH_TOKEN"
python3 out/ksu/helper/avd-ksu.py patch --image-dir "$image" --variant kernelsu --version v3.3.1 --allow-shell --out "$GITHUB_WORKSPACE/out/ksu/patched-ramdisk.img" >out/ksu/patch-log.txt 2>&1 || { tail -n 100 out/ksu/patch-log.txt; exit 2; }
test -s out/ksu/patched-ramdisk.img
sha256sum "$image/ramdisk.img" out/ksu/patched-ramdisk.img >out/ksu/ramdisk-hashes.txt
curl --fail --location --retry 3 "https://github.com/tiann/KernelSU/releases/download/v3.3.1/KernelSU_v3.3.1_32680-release.apk" --output out/ksu/manager.apk
echo 'b4a059ace71de2fa65cc7f12b1c58d55fc23ab25e057ee4230ce779742abe450  out/ksu/manager.apk' | sha256sum -c - | tee out/ksu/manager-hash-verified.txt
buildtool="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n1)"
"$buildtool/aapt" dump badging out/ksu/manager.apk >out/ksu/manager-badging.txt
# Historical x86 KernelSU probe keeps its exact source-locked checks.
# The new ARM64-product/native-bridge gate stages its OWN same-SHA Go/Rust
# artifact and does NOT compile or reuse the historical x86 probe.
if [[ "${WBD_KSU_PRODUCT_ARM64:-0}" == 1 || "${WBD_KSU_PRODUCT_X86_CI:-0}" == 1 ]]; then
  test -s out/android-root-app-native/SOURCE
  test "$(cat out/android-root-app-native/SOURCE)" = "$GITHUB_SHA"
  (cd out/android-root-app-native && sha256sum -c SHA256SUMS) >out/ksu/native-checksums.txt
  if [[ "${WBD_KSU_PRODUCT_X86_CI:-0}" == 1 ]]; then
    test -s out/android-root-app-native/manifest-ci-x86_64.json
    test -s out/android-root-app-native/wbd-v4-client-amd64
    test -s out/android-root-app-native/libwbd_engine-amd64.so
    echo "KSU_NATIVE_PRODUCT_X86_CI_SOURCE_LOCKED" >out/ksu/native-source-mode.txt
  else
    echo "KSU_NATIVE_PRODUCT_ARM64_SOURCE_LOCKED" >out/ksu/native-source-mode.txt
  fi
else
  (cd out/native && sha256sum -c SHA256SUMS) >out/ksu/native-checksums.txt
  test "$(cat out/native/SOURCE)" = "$GITHUB_SHA"
fi
