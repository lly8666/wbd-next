#!/usr/bin/env bash
# Independent *actual* ARM64 Root APK, never the old VpnService or a probe.
# Copies ONLY the exact original-Go executable + original shared Rust .so
# produced by the SAME SOURCE Android ARM64 native job; no crypto/JNI fork.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?}"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA:?}"
: "${ANDROID_HOME:?}"
native="out/android-root-app-native"
test -s "$native/SOURCE" && test "$(cat "$native/SOURCE")" = "$GITHUB_SHA"
for f in manifest.json wbd-v4-client-arm64 libwbd_engine-arm64.so;do
  test -s "$native/$f"
done
mkdir -p out/android-root-app/classes out/android-root-app/dex
assets="out/android-root-app/assets/native-arm64"
mkdir -p "$assets"
# Source/ABI/hash fail-closed gate. This signed APK must never mix an
# app generated at SOURCE B with a Go/Rust ELF generated at SOURCE A.
python3 - <<'PY'
import hashlib,json,os,pathlib,struct
n=pathlib.Path("out/android-root-app-native")
m=json.loads((n/"manifest.json").read_text())
assert m["source"]==os.environ["GITHUB_SHA"]
assert m["go_os"]=="android" and m["android_abis"]==["arm64"]
assert m["go_build_tags"]=="wbd_v4_embedded_go"
for name in ["wbd-v4-client-arm64","libwbd_engine-arm64.so"]:
    p=n/name;b=p.read_bytes()
    assert hashlib.sha256(b).hexdigest()==m["artifacts"][name]["sha256"]
    assert b[:5]==b"\x7fELF\x02",name
    assert struct.unpack_from("<H",b,18)[0]==183,name
    po=struct.unpack_from("<Q",b,32)[0]
    es,num=struct.unpack_from("<HH",b,54)
    aligns=[struct.unpack_from("<Q",b,po+i*es+48)[0]
        for i in range(num) if struct.unpack_from("<I",b,po+i*es)[0]==1]
    assert aligns and min(aligns)>=16384,(name,aligns)
print("ANDROID_ROOT_APP_NATIVE_SOURCE_AND_AARCH64_16K_PASS",m["source"])
PY
cp "$native/manifest.json" "$native/SOURCE" "$native/wbd-v4-client-arm64" \
   "$native/libwbd_engine-arm64.so" "$assets/"
# The real original-Go cold loader requires the very same immutable B2
# source and provenances. The CI artifact is a dependency, NEVER a runtime
# phone download or a synthetic local rule list.
cn="out/android-root-app-cn"
python3 - <<'PY'
from pathlib import Path
import hashlib,json,os
cn=Path("out/android-root-app-cn")
receipt=json.loads((cn/"receipt.json").read_text())
meta=json.loads((cn/"cn-geosite-provenance.json").read_text())
source=os.environ["GITHUB_SHA"]
rev="41504eae2a11f305fe88cfc605cf6c105a80bf5a"
expected="45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6"
raw=(cn/"wbd-cn-geosite.txt").read_bytes()
license=(cn/"wbd-cn-geosite-license.txt").read_text()
assert receipt["schema"]=="wbd-android-b2-pinned-cn-geosite-go-loopback/v1"
assert receipt["source"]==source and receipt["pinned_rules_sha256"]==expected
assert meta["source_commit"]==rev and meta["source"]=="v2fly/domain-list-community"
assert meta["output_distinct_rules"]==8503
assert meta["text_sha256"]==expected==hashlib.sha256(raw).hexdigest()
assert len(raw)>10000 and len(raw)<6000000 and raw.endswith(b"\n")
assert meta["kinds"]=={"domain":8431,"full":69,"regexp":3}
assert "MIT License" in license and "V2Ray" in license
print("ANDROID_B2B_SIGNED_ROOT_APP_RULES_SOURCE_SHA_LICENSE_VERIFIED",source)
PY
cp "$cn/wbd-cn-geosite.txt" "$cn/wbd-cn-geosite-license.txt" \
   "$cn/cn-geosite-provenance.json" "$assets/"
# This DEBUG-only helper tests actual kernel TUN, AF_PACKET and underlay
# without implementing any alternate WBD TLS, Rust AEAD or packet loop.
# Unlike the KSU x86 Bridge test libraries, it is an AArch64 Bionic ELF,
# separate from the production client, signed into this debug APK only.
ndk="$(find "$ANDROID_HOME/ndk" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n 1)"
tool="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin"
test -x "$tool/aarch64-linux-android28-clang"
"$tool/aarch64-linux-android28-clang" -std=c11 -O2 -fPIE -pie \
  -Wall -Wextra -Werror -Wl,-z,max-page-size=16384 \
  android/root-app/ci/device-selftest-arm64.c \
  -o "$assets/device-selftest-arm64"
sha256sum "$assets/device-selftest-arm64" | awk '{print $1}' \
  > "$assets/device-selftest-sha256.txt"
python3 - <<'PY'
from pathlib import Path
import struct,hashlib
p=Path("out/android-root-app/assets/native-arm64/device-selftest-arm64")
b=p.read_bytes()
assert b[:5]==b"\x7fELF\x02" and struct.unpack_from("<H",b,18)[0]==183
po=struct.unpack_from("<Q",b,32)[0]
es,num=struct.unpack_from("<HH",b,54)
aligns=[struct.unpack_from("<Q",b,po+i*es+48)[0]
 for i in range(num) if struct.unpack_from("<I",b,po+i*es)[0]==1]
assert aligns and min(aligns)>=16384
assert hashlib.sha256(b).hexdigest()==(p.parent/"device-selftest-sha256.txt").read_text().strip()
print("ANDROID_ARM64_ROOT_DEBUG_ONLY_TUN_RAW_SELFTEST_ABI_SHA_PASS")
PY
sdk="$ANDROID_HOME"
bt="$(find "$sdk/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n1)"
for name in aapt2 d8 apksigner zipalign aapt; do test -x "$bt/$name"; done
if test -f "$sdk/platforms/android-36/android.jar";then
  jar="$sdk/platforms/android-36/android.jar"; api=36
elif test -f "$sdk/platforms/android-35/android.jar";then
  jar="$sdk/platforms/android-35/android.jar"; api=35
else
  echo "ANDROID_ARM64_ROOT_APP_NEEDS_API35_ANDROID_SDK" >&2;exit 2
fi
find android/root-app/src -name '*.java' -print0 |
  xargs -0 javac -encoding UTF-8 -source 8 -target 8 -classpath "$jar" \
    -d out/android-root-app/classes
"$bt/d8" --min-api 28 --lib "$jar" \
    --output out/android-root-app/dex \
    $(find out/android-root-app/classes -name '*.class' -print)
"$bt/aapt2" link --manifest android/root-app/AndroidManifest.xml \
    -I "$jar" -A out/android-root-app/assets \
    --min-sdk-version 28 --target-sdk-version 35 \
    -o out/android-root-app/unsigned.apk
(cd out/android-root-app/dex && zip -q -j ../unsigned.apk classes.dex)
"$bt/zipalign" -f 4 \
    out/android-root-app/unsigned.apk out/android-root-app/aligned.apk
# Debug-signing key is disposable and stays ONLY on the runner.
keytool -genkeypair -alias wbdroot \
    -keystore out/android-root-app/disposable-debug.jks \
    -storepass android -keypass android \
    -dname "CN=Disposable WBD ARM64 Root,O=Experimental,C=US" \
    -keyalg RSA -keysize 2048 -validity 2 -noprompt >/dev/null 2>&1
"$bt/apksigner" sign \
    --ks out/android-root-app/disposable-debug.jks \
    --ks-key-alias wbdroot --ks-pass pass:android --key-pass pass:android \
    --out out/android-root-app/wbd-root-arm64-debug.apk \
    out/android-root-app/aligned.apk
"$bt/apksigner" verify out/android-root-app/wbd-root-arm64-debug.apk
# Exact same signed original Go/Rust product APK, with a readable Lite
# beta filename in the GitHub artifact. No second or mock WBD binary.
cp out/android-root-app/wbd-root-arm64-debug.apk \
   out/android-root-app/wbd-root-lite-arm64-debug.apk
"$bt/aapt" dump badging out/android-root-app/wbd-root-arm64-debug.apk \
    >out/android-root-app/badging.txt
grep -F "package: name='org.wbdnext.rootclient'" out/android-root-app/badging.txt
grep -F "targetSdkVersion:'35'" out/android-root-app/badging.txt
"$bt/aapt" dump xmltree out/android-root-app/wbd-root-arm64-debug.apk \
    AndroidManifest.xml >out/android-root-app/manifest-tree.txt
if grep -Eq 'BIND_VPN_SERVICE|VpnService|android.net.VpnService' \
    out/android-root-app/manifest-tree.txt;then
  echo "ANDROID_ROOT_PRODUCT_MUST_NOT_CONTAIN_VPN_SERVICE" >&2;exit 1
fi
python3 - <<'PY'
import xml.etree.ElementTree as ET
x=ET.parse("android/root-app/AndroidManifest.xml").getroot()
ns="{http://schemas.android.com/apk/res/android}"
q=x.find("queries")
assert q is not None,"package visibility must be scoped"
assert any(e.find("action").get(ns+"name")=="android.intent.action.MAIN" and
           e.find("category").get(ns+"name")=="android.intent.category.LAUNCHER"
           for e in q.findall("intent")),"only explicitly query launchable packages"
assert all(p.get(ns+"name")!="android.permission.QUERY_ALL_PACKAGES"
           for p in x.findall("uses-permission")),"no broad package visibility"
print("ANDROID_ROOT_NARROW_INSTALLED_PACKAGE_VISIBILITY_MANIFEST_PASS")
PY
python3 - <<'PY'
from pathlib import Path
import hashlib,json,os,zipfile
out=Path("out/android-root-app")
apk=out/"wbd-root-arm64-debug.apk"
with zipfile.ZipFile(apk) as z:
    expected=["classes.dex","assets/native-arm64/manifest.json",
        "assets/native-arm64/SOURCE",
        "assets/native-arm64/wbd-v4-client-arm64",
        "assets/native-arm64/libwbd_engine-arm64.so",
        "assets/native-arm64/wbd-cn-geosite.txt",
        "assets/native-arm64/wbd-cn-geosite-license.txt",
        "assets/native-arm64/cn-geosite-provenance.json",
        "assets/native-arm64/device-selftest-arm64",
        "assets/native-arm64/device-selftest-sha256.txt"]
    for name in expected:assert name in z.namelist(),name
    assert z.read("assets/native-arm64/SOURCE").decode().strip()==os.environ["GITHUB_SHA"]
    m=json.loads(z.read("assets/native-arm64/manifest.json"))
    for name in ["wbd-v4-client-arm64","libwbd_engine-arm64.so"]:
        b=z.read("assets/native-arm64/"+name)
        assert hashlib.sha256(b).hexdigest()==m["artifacts"][name]["sha256"]
    geosite=z.read("assets/native-arm64/wbd-cn-geosite.txt")
    license=z.read("assets/native-arm64/wbd-cn-geosite-license.txt")
    provenance=json.loads(z.read("assets/native-arm64/cn-geosite-provenance.json"))
    assert hashlib.sha256(geosite).hexdigest()=="45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6"
    assert provenance["source_commit"]=="41504eae2a11f305fe88cfc605cf6c105a80bf5a"
    assert provenance["text_sha256"]==hashlib.sha256(geosite).hexdigest()
    assert provenance["output_distinct_rules"]==8503
    assert b"MIT License" in license and b"V2Ray" in license
    diag=z.read("assets/native-arm64/device-selftest-arm64")
    assert hashlib.sha256(diag).hexdigest()==z.read(
        "assets/native-arm64/device-selftest-sha256.txt").decode().strip()
    assert diag[:5]==b"\x7fELF\x02" and int.from_bytes(diag[18:20],"little")==183
    assert not any("x86" in name for name in z.namelist())
summary={"schema":"wbd-android-arm64-root-app-source-locked/v1",
    "source":os.environ["GITHUB_SHA"],
    "arm64_native_source":os.environ["GITHUB_SHA"],
    "platform":"Android ARM64-v8a ONLY","mode":"original Go Normal/off",
    "package":"org.wbdnext.rootclient",
    "edition":"Root Lite v2 short-key offline beta",
    "short_key_v2_java_and_cache":"COMPILED_HOST_TESTED_DEVICE_NOT_RUN",
    "target_sdk":35,"minimum_sdk":28,
    "go_rust_apk_assets_verified":True,
    "pinned_cn_8503_in_signed_apk_verified":True,
    "pinned_cn_original_go_cold_loader":"COMPILED_NOT_ANDROID_EXECUTED",
    "android_system_dns_interception":"NOT_CONNECTED",
    "no_vpn_service_manifest_verified":True,
    "debug_only_tun_raw_uid_routing_selftest_asset":True,
    "device_kernel_selftest_execution":"NOT_RUN",
    "root_phone_installed":"NOT_RUN","real_tls_data_stop":"NOT_RUN",
    "apk_sha256":hashlib.sha256(apk.read_bytes()).hexdigest()}
(out/"manifest.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
(out/"SOURCE").write_text(os.environ["GITHUB_SHA"]+"\n")
PY
(cd out/android-root-app && sha256sum wbd-root-arm64-debug.apk \
    wbd-root-lite-arm64-debug.apk \
    SOURCE manifest.json badging.txt manifest-tree.txt >SHA256SUMS &&
    sha256sum -c SHA256SUMS)
rm -f out/android-root-app/disposable-debug.jks \
    out/android-root-app/unsigned.apk out/android-root-app/aligned.apk
echo "ANDROID_ROOT_ARM64_APP_AND_NATIVE_ASSETS_SOURCE_LOCKED_BUILD_PASS sdk=$api"
