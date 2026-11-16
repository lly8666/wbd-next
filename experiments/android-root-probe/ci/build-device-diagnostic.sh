#!/usr/bin/env bash
# Self-contained physical-device diagnostic APK (arm64-v8a + x86_64).
# The package is signed with the SAME disposable per-run key as the KSU app,
# so emulator CI can verify app->su after a same-signature package upgrade.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
out="out/diag"
mkdir -p "$out/native-payload/lib/arm64-v8a" "$out/native-payload/lib/x86_64"
( cd out/native && sha256sum -c SHA256SUMS )
test -s out/apk/temporary.jks
test "$(cat out/apk/SOURCE)" = "$GITHUB_SHA"
test "$(cat out/native/SOURCE)" = "$GITHUB_SHA"
test -s out/apk/dex/classes.dex
sdk="$ANDROID_HOME"
tools="$(find "$sdk/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n1)"
compile_api="$(cat out/apk/compile-api.txt)"
test "$compile_api" = 36 -o "$compile_api" = 37
jar="$sdk/platforms/android-$compile_api/android.jar"
test -s "$jar"
cp out/native/bin/probe-aarch64-linux-android "$out/native-payload/lib/arm64-v8a/libwbdprobe.so"
cp out/native/bin/probe-x86_64-linux-android "$out/native-payload/lib/x86_64/libwbdprobe.so"
readelf -h "$out/native-payload/lib/arm64-v8a/libwbdprobe.so" > "$out/elf-arm64-header.txt"
readelf -h "$out/native-payload/lib/x86_64/libwbdprobe.so" > "$out/elf-x86_64-header.txt"
readelf -lW "$out/native-payload/lib/arm64-v8a/libwbdprobe.so" > "$out/elf-arm64-loads.txt"
readelf -lW "$out/native-payload/lib/x86_64/libwbdprobe.so" > "$out/elf-x86_64-loads.txt"
grep -q 'AArch64' "$out/elf-arm64-header.txt"
grep -q 'X86-64' "$out/elf-x86_64-header.txt"
for abi in arm64 x86_64;do
  grep -Eq 'LOAD .*0x4000' "$out/elf-$abi-loads.txt" || {
    echo "ELF_LOAD_ALIGNMENT_NOT_16K $abi";exit 1;
  }
done
mkdir -p "$out/assets"
# Historical, date-pinned APNIC CN allocation snapshot. This is NOT an IP
# geolocation truth set and MUST NOT be silently replaced by incomplete data.
curl --fail --location --retry 3 --connect-timeout 15 --max-time 100 \
 "https://ftp.apnic.net/stats/apnic/delegated-apnic-20261116" \
 --output "$out/apnic-delegated-20261116.txt"
python3 experiments/android-root-probe/ci/cn-ipv4-snapshot.py \
 "$out/apnic-delegated-20261116.txt" "$out/assets"
cp "$out/assets/cn-ipv4-provenance.json" "$out/cn-ipv4-provenance.json"
# Full pinned geolocation-cn graph: includes/attributes/affiliations and
# domain/full/keyword/regexp are flattened into an audited DNS-only asset.
# Fixed commit, pinned digest, and MIT license travel with each debug APK.
curl --fail --location --retry 3 --connect-timeout 15 --max-time 120 \
 "https://codeload.github.com/v2fly/domain-list-community/zip/41504eae2a11f305fe88cfc605cf6c105a80bf5a" \
 --output "$out/cn-geosite-upstream.zip"
python3 experiments/android-root-probe/ci/cn-geosite-snapshot.py \
 "$out/cn-geosite-upstream.zip" "$out/assets"
cp "$out/assets/cn-geosite-provenance.json" "$out/cn-geosite-provenance.json"
rm -f "$out/cn-geosite-upstream.zip"
rm -f "$out/apnic-delegated-20261116.txt"
printf '%s\n' "$GITHUB_SHA" >"$out/assets/wbd-diagnostic-source.txt"
"$tools/aapt2" link --manifest experiments/android-root-probe/app/DeviceDiagnosticManifest.xml \
 -I "$jar" -A "$out/assets" --min-sdk-version 28 --target-sdk-version 37 \
 -o "$out/unsigned.apk"
(cd out/apk/dex; zip -q -j ../../diag/unsigned.apk classes.dex)
(cd "$out/native-payload"; zip -q -0 -r ../unsigned.apk lib)
"$tools/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
"$tools/apksigner" sign --ks out/apk/temporary.jks --ks-key-alias probe \
 --ks-pass pass:android --key-pass pass:android \
 --out "$out/device-diagnostic.apk" "$out/aligned.apk"
"$tools/apksigner" verify --verbose --print-certs "$out/device-diagnostic.apk" >"$out/apksigner-verify.txt"
"$tools/aapt" dump badging "$out/device-diagnostic.apk" >"$out/badging.txt"
grep -q "targetSdkVersion:'37'" "$out/badging.txt"
grep -q "sdkVersion:'28'" "$out/badging.txt"
grep -q "package: name='org.wbdnext.rootprobe'" "$out/badging.txt"
"$tools/aapt2" dump xmltree --file AndroidManifest.xml "$out/device-diagnostic.apk" >"$out/manifest-xmltree.txt"
grep -q 'extractNativeLibs' "$out/manifest-xmltree.txt"
python3 - <<'PY'
import hashlib,json,os,zipfile
from pathlib import Path
p=Path("out/diag");apk=p/"device-diagnostic.apk"
with zipfile.ZipFile(apk) as z:
 libs=[f"lib/{abi}/libwbdprobe.so" for abi in ("arm64-v8a","x86_64")]
 for name in libs:
  i=z.getinfo(name)
  assert i.compress_type==zipfile.ZIP_STORED,(name,i.compress_type)
  assert i.file_size>200000,(name,i.file_size)
 assert z.read("assets/wbd-diagnostic-source.txt").strip().decode()==os.environ["GITHUB_SHA"]
 assert z.getinfo("assets/wbd-cn-ipv4.txt").file_size>10000
 assert z.getinfo("assets/cn-ipv4-provenance.json").file_size>100
 assert 10000<z.getinfo("assets/wbd-cn-geosite.txt").file_size<6000000
 assert z.getinfo("assets/cn-geosite-provenance.json").file_size>100
 assert z.getinfo("assets/wbd-cn-geosite-license.txt").file_size>100
 geo=json.loads(z.read("assets/cn-geosite-provenance.json"))
 assert geo["source_commit"]=="41504eae2a11f305fe88cfc605cf6c105a80bf5a"
 assert hashlib.sha256(z.read("assets/wbd-cn-geosite.txt")).hexdigest()==geo["text_sha256"]
 assert geo["output_distinct_rules"]>1000
 assert z.getinfo("classes.dex").file_size>2000
def sha(b):return hashlib.sha256(b).hexdigest()
m={
 "schema":"android-wbd-physical-root-self-contained-apk/v1",
 "source":os.environ["GITHUB_SHA"],"apk":"device-diagnostic.apk",
 "apk_sha256":sha(apk.read_bytes()),
 "min_sdk":28,"target_sdk":37,
 "supported_abis":["arm64-v8a","x86_64"],
 "arm64_elf_sha256":sha((p/"native-payload/lib/arm64-v8a/libwbdprobe.so").read_bytes()),
 "x86_64_elf_sha256":sha((p/"native-payload/lib/x86_64/libwbdprobe.so").read_bytes()),
 "elf_load_alignment":"0x4000 PT_LOAD",
 "native_execution":"extractNativeLibs=true; App nativeLibraryDir/libwbdprobe.so via actual su; no ADB push",
 "cn_ipv4_provenance":json.loads((p/"cn-ipv4-provenance.json").read_text()),
 "cn_geosite_provenance":json.loads((p/"cn-geosite-provenance.json").read_text()),
 "cn_ipv4_note":"APNIC CN allocated/assigned, not IP geolocation",
 "cn_domain_note":"fixed full geolocation-cn include/attribute graph with exact/suffix/keyword/regexp, tested at DNS classification only",
 "root_installer":False,"vpn_client":False,"vpn_service":False,
 "wifi_usb_physical_traffic":"NOT_RUN",
 "signing":"disposable per-run CI test key; uninstall debug package after test",
 "cert_per_run":"not reusable across reruns; uninstall before installing different signed build",
 "evidence":"user-triggered reports in files/last-device-diagnostic.json; share via Android ACTION_SEND"
}
(p/"manifest.json").write_text(json.dumps(m,indent=2)+"\n")
PY
echo "$GITHUB_SHA" >"$out/SOURCE"
( cd "$out"; sha256sum device-diagnostic.apk SOURCE manifest.json badging.txt apksigner-verify.txt elf-arm64-header.txt elf-x86_64-header.txt elf-arm64-loads.txt elf-x86_64-loads.txt cn-ipv4-provenance.json cn-geosite-provenance.json >SHA256SUMS )
( cd "$out"; sha256sum -c SHA256SUMS )
rm -f out/apk/temporary.jks "$out/unsigned.apk" "$out/aligned.apk"
rm -rf "$out/native-payload" "$out/assets"
echo "PACKAGED_ANDROID_ARM64_X86_64_DIAGNOSTIC_APK"
