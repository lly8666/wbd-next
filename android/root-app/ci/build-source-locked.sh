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
        "assets/native-arm64/libwbd_engine-arm64.so"]
    for name in expected:assert name in z.namelist(),name
    assert z.read("assets/native-arm64/SOURCE").decode().strip()==os.environ["GITHUB_SHA"]
    m=json.loads(z.read("assets/native-arm64/manifest.json"))
    for name in ["wbd-v4-client-arm64","libwbd_engine-arm64.so"]:
        b=z.read("assets/native-arm64/"+name)
        assert hashlib.sha256(b).hexdigest()==m["artifacts"][name]["sha256"]
    assert not any("x86" in name for name in z.namelist())
summary={"schema":"wbd-android-arm64-root-app-source-locked/v1",
    "source":os.environ["GITHUB_SHA"],
    "arm64_native_source":os.environ["GITHUB_SHA"],
    "platform":"Android ARM64-v8a ONLY","mode":"original Go Normal/off",
    "package":"org.wbdnext.rootclient",
    "target_sdk":35,"minimum_sdk":28,
    "go_rust_apk_assets_verified":True,
    "no_vpn_service_manifest_verified":True,
    "root_phone_installed":"NOT_RUN","real_tls_data_stop":"NOT_RUN",
    "apk_sha256":hashlib.sha256(apk.read_bytes()).hexdigest()}
(out/"manifest.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
(out/"SOURCE").write_text(os.environ["GITHUB_SHA"]+"\n")
PY
(cd out/android-root-app && sha256sum wbd-root-arm64-debug.apk \
    SOURCE manifest.json badging.txt manifest-tree.txt >SHA256SUMS &&
    sha256sum -c SHA256SUMS)
rm -f out/android-root-app/disposable-debug.jks \
    out/android-root-app/unsigned.apk out/android-root-app/aligned.apk
echo "ANDROID_ROOT_ARM64_APP_AND_NATIVE_ASSETS_SOURCE_LOCKED_BUILD_PASS sdk=$api"
