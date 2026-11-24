#!/usr/bin/env bash
# Same original Android Java controller, Go TLS, Rust M4; x86_64 CI-only APK.
# NEVER published as the ARM64 product; no VPN, fake TLS or second packet pump.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
: "$ANDROID_HOME"
n=out/android-root-app-native
cn=out/android-root-app-cn
out=out/android-x86-ci-app
test "$(cat "$n/SOURCE")" = "$GITHUB_SHA"
test -s "$n/manifest-ci-x86_64.json"
test -s "$n/wbd-v4-client-amd64"
test -s "$n/libwbd_engine-amd64.so"
(cd "$n" && sha256sum -c SHA256SUMS) >"$n/ci-native-verify.txt"
python3 - <<'PY'
from pathlib import Path
import os,json,hashlib,struct
n=Path("out/android-root-app-native")
m=json.loads((n/"manifest-ci-x86_64.json").read_text())
assert m["source"]==os.environ["GITHUB_SHA"]
assert m["android_abis"]==["x86_64"] and m["go_os"]=="android"
assert m["release"] is False
assert m["go_build_tags"]=="wbd_v4_embedded_go"
for name in ("wbd-v4-client-amd64","libwbd_engine-amd64.so"):
    b=(n/name).read_bytes()
    assert hashlib.sha256(b).hexdigest()==m["artifacts"][name]["sha256"]
    assert b[:5]==b"\x7fELF\x02" and struct.unpack_from("<H",b,18)[0]==62
print("ANDROID_X86_CI_NATIVE_SAME_SOURCE_ELF62_ABI_PASS")
cn=Path("out/android-root-app-cn")
receipt=json.loads((cn/"receipt.json").read_text())
p=json.loads((cn/"cn-geosite-provenance.json").read_text())
assert receipt["source"]==os.environ["GITHUB_SHA"]
sha=p["text_sha256"]
assert receipt["active_cn"]==p
assert p["text_sha256"]==sha==hashlib.sha256((cn/"wbd-cn-geosite.txt").read_bytes()).hexdigest()
assert p["output_distinct_rules"]>1000
assert "MIT License" in (cn/"wbd-cn-geosite-license.txt").read_text()
PY
mkdir -p "$out/classes" "$out/dex" "$out/assets/native-amd64"
assets="$out/assets/native-amd64"
cp "$n/manifest-ci-x86_64.json" "$assets/manifest.json"
cp "$n/SOURCE" "$n/wbd-v4-client-amd64" "$n/libwbd_engine-amd64.so" "$assets/"
cp "$cn/wbd-cn-geosite.txt" "$cn/wbd-cn-geosite-license.txt" \
   "$cn/cn-geosite-provenance.json" "$assets/"
python3 - "$cn" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1])
meta=json.loads((p/"cn-ipv4-provenance.json").read_text())
raw=(p/"wbd-cn-ipv4.txt").read_bytes()
assert meta["source_date_utc"]=="2026-11-16"
assert 1000<meta["cn_collapsed_prefixes"]<=8192
assert len(raw)<=256*1024 and hashlib.sha256(raw).hexdigest()==meta["cidr_sha256"]
PY
cp "$cn/wbd-cn-ipv4.txt" "$cn/cn-ipv4-provenance.json" "$assets/"
sdk="$ANDROID_HOME"
bt="$(find "$sdk/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n1)"
for tool in aapt2 d8 apksigner zipalign aapt;do test -x "$bt/$tool";done
if test -f "$sdk/platforms/android-36/android.jar";then
  jar="$sdk/platforms/android-36/android.jar"
else
  jar="$sdk/platforms/android-35/android.jar"
fi
find android/root-app/src -name '*.java' -print0 |
  xargs -0 javac -encoding UTF-8 -source 8 -target 8 -classpath "$jar" \
    -d "$out/classes"
# CI ONLY: a bounded app-UID KernelSU authorization test; never built into
# the release ARM64 signed APK, never handles a WBD data packet.
javac -encoding UTF-8 -source 8 -target 8 -classpath "$jar:$out/classes" \
  -d "$out/classes" android/root-app/ci/X86CiAppSuActivity.java \
    android/root-app/ci/X86CiOriginalStartActivity.java \
    android/root-app/ci/RootConnectionSettingsTest.java \
    android/root-app/ci/RootConnectionProfileBundleTest.java \
    android/root-app/ci/OriginalGoCommandArgsTest.java \
    android/root-app/ci/RootColdRotationTest.java \
    android/root-app/ci/RootForegroundAutoReconnectTest.java \
    android/root-app/ci/NetworkScopeGateTest.java
python3 - <<'PYCI'
import xml.etree.ElementTree as ET
from pathlib import Path
path=Path("android/root-app/AndroidManifest.xml")
target=Path("out/android-x86-ci-app/ci-only-AndroidManifest.xml")
ns="http://schemas.android.com/apk/res/android"
ET.register_namespace("android",ns)
tree=ET.parse(path)
root=tree.getroot()
app=root.find("application")
assert app is not None
app.set("{"+ns+"}label","@string/wbd_x86_ci_label")
ET.SubElement(app,"activity",{
    "{"+ns+"}name":".X86CiAppSuActivity",
    "{"+ns+"}exported":"true"})
ET.SubElement(app,"activity",{
    "{"+ns+"}name":".X86CiOriginalStartActivity",
    "{"+ns+"}exported":"true"})
tree.write(target,encoding="utf-8",xml_declaration=True)
PYCI
# AAPT2 must link a COMPILED string resource. A literal manifest label
# is omitted by this no-resources aapt2 build (observed blank badging).
# KSU Manager must display the exact CI-only label before UI authorization.
mkdir -p "$out/res/values" "$out/res-compiled"
printf '%s\n' '<?xml version="1.0" encoding="utf-8"?>' \
 '<resources><string name="wbd_x86_ci_label">WBD x86 CI Root</string></resources>' \
 >"$out/res/values/ci_label.xml"
"$bt/aapt2" compile --dir "$out/res" -o "$out/res-compiled"
mapfile -t ci_flats < <(find "$out/res-compiled" -type f -name '*.flat' | sort)
test "${#ci_flats[@]}" -eq 1
"$bt/d8" --min-api 28 --lib "$jar" --output "$out/dex" \
  $(find "$out/classes" -name '*.class' -print)
# This is an app-local new resource over android.jar imported via -I.
# AAPT2 explicitly requires auto-add-overlay for a new compiled -R entry.
"$bt/aapt2" link --auto-add-overlay --manifest "$out/ci-only-AndroidManifest.xml" \
  -I "$jar" -A "$out/assets" -R "${ci_flats[0]}" \
  --min-sdk-version 28 --target-sdk-version 35 \
  -o "$out/unsigned.apk"
(cd "$out/dex" && zip -q -j ../unsigned.apk classes.dex)
"$bt/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
keytool -genkeypair -alias wbdroot -keystore "$out/ci-disposable.jks" \
  -storepass android -keypass android \
  -dname "CN=CI-only WBD x86 Android,O=Experiment,C=US" \
  -keyalg RSA -keysize 2048 -validity 2 -noprompt >/dev/null 2>&1
"$bt/apksigner" sign --ks "$out/ci-disposable.jks" \
  --ks-key-alias wbdroot --ks-pass pass:android --key-pass pass:android \
  --out "$out/wbd-root-x86-ci-only.apk" "$out/aligned.apk"
"$bt/apksigner" verify "$out/wbd-root-x86-ci-only.apk"
"$bt/aapt" dump badging "$out/wbd-root-x86-ci-only.apk" >"$out/badging.txt"
grep -F "package: name='org.wbdnext.rootclient'" "$out/badging.txt"
grep -F "application-label:'WBD x86 CI Root'" "$out/badging.txt"
"$bt/aapt" dump xmltree "$out/wbd-root-x86-ci-only.apk" AndroidManifest.xml \
  >"$out/manifest-tree.txt"
grep -Fq "X86CiAppSuActivity" "$out/manifest-tree.txt"
grep -Fq "X86CiOriginalStartActivity" "$out/manifest-tree.txt"
if grep -Eq 'BIND_VPN_SERVICE|VpnService' "$out/manifest-tree.txt";then
 echo "X86_CI_MUST_NOT_CONTAIN_VPN_SERVICE" >&2;exit 1
fi
python3 - <<'PY'
from pathlib import Path
import hashlib,json,os,zipfile,struct
o=Path("out/android-x86-ci-app")
apk=o/"wbd-root-x86-ci-only.apk"
with zipfile.ZipFile(apk) as z:
    names=z.namelist()
    required=["classes.dex","assets/native-amd64/manifest.json",
      "assets/native-amd64/SOURCE","assets/native-amd64/wbd-v4-client-amd64",
      "assets/native-amd64/libwbd_engine-amd64.so",
      "assets/native-amd64/wbd-cn-geosite.txt",
      "assets/native-amd64/wbd-cn-geosite-license.txt",
      "assets/native-amd64/cn-geosite-provenance.json"]
    assert all(x in names for x in required)
    assert not any("native-arm64/" in x for x in names)
    assert "X86CiAppSuActivity" in (o/"manifest-tree.txt").read_text()
    assert "X86CiOriginalStartActivity" in (o/"manifest-tree.txt").read_text()
    assert "X86CiAppSuActivity.java" not in names
    m=json.loads(z.read("assets/native-amd64/manifest.json"))
    assert m["source"]==os.environ["GITHUB_SHA"]==z.read("assets/native-amd64/SOURCE").decode().strip()
    assert m["release"] is False and m["android_abis"]==["x86_64"]
    for n in ("wbd-v4-client-amd64","libwbd_engine-amd64.so"):
        b=z.read("assets/native-amd64/"+n)
        assert hashlib.sha256(b).hexdigest()==m["artifacts"][n]["sha256"]
        assert struct.unpack_from("<H",b,18)[0]==62
    cn_meta=json.loads(z.read("assets/native-amd64/cn-geosite-provenance.json"))
    assert hashlib.sha256(z.read("assets/native-amd64/wbd-cn-geosite.txt")).hexdigest()==cn_meta["text_sha256"]
    assert b"MIT License" in z.read("assets/native-amd64/wbd-cn-geosite-license.txt")
summary={"schema":"wbd-android-x86-ci-only-original-go-rust/v1",
 "source":os.environ["GITHUB_SHA"],"release":False,"android_abi":"x86_64",
 "actual_guest_app_su":"NOT_RUN","actual_guest_go_rust":"NOT_RUN",
 "original_tls_auth_lease_m4_tcp_udp_stop":"NOT_RUN",
 "apk_sha256":hashlib.sha256(apk.read_bytes()).hexdigest()}
(o/"manifest.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
(o/"SOURCE").write_text(os.environ["GITHUB_SHA"]+"\n")
print("ANDROID_X86_CI_ONLY_SIGNED_ORIGINAL_GO_RUST_APK_BUILD_PASS")
PY
(cd "$out" && sha256sum wbd-root-x86-ci-only.apk SOURCE manifest.json >SHA256SUMS && sha256sum -c SHA256SUMS)
rm -f "$out/ci-disposable.jks" "$out/unsigned.apk" "$out/aligned.apk"
