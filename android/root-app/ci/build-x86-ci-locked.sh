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
sha="45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6"
assert p["text_sha256"]==sha==hashlib.sha256((cn/"wbd-cn-geosite.txt").read_bytes()).hexdigest()
assert p["output_distinct_rules"]==8503
assert "MIT License" in (cn/"wbd-cn-geosite-license.txt").read_text()
PY
mkdir -p "$out/classes" "$out/dex" "$out/assets/native-amd64"
assets="$out/assets/native-amd64"
cp "$n/manifest-ci-x86_64.json" "$assets/manifest.json"
cp "$n/SOURCE" "$n/wbd-v4-client-amd64" "$n/libwbd_engine-amd64.so" "$assets/"
cp "$cn/wbd-cn-geosite.txt" "$cn/wbd-cn-geosite-license.txt" \
   "$cn/cn-geosite-provenance.json" "$assets/"
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
"$bt/d8" --min-api 28 --lib "$jar" --output "$out/dex" \
  $(find "$out/classes" -name '*.class' -print)
"$bt/aapt2" link --manifest android/root-app/AndroidManifest.xml \
  -I "$jar" -A "$out/assets" \
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
"$bt/aapt" dump xmltree "$out/wbd-root-x86-ci-only.apk" AndroidManifest.xml \
  >"$out/manifest-tree.txt"
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
    m=json.loads(z.read("assets/native-amd64/manifest.json"))
    assert m["source"]==os.environ["GITHUB_SHA"]==z.read("assets/native-amd64/SOURCE").decode().strip()
    assert m["release"] is False and m["android_abis"]==["x86_64"]
    for n in ("wbd-v4-client-amd64","libwbd_engine-amd64.so"):
        b=z.read("assets/native-amd64/"+n)
        assert hashlib.sha256(b).hexdigest()==m["artifacts"][n]["sha256"]
        assert struct.unpack_from("<H",b,18)[0]==62
    assert hashlib.sha256(z.read("assets/native-amd64/wbd-cn-geosite.txt")).hexdigest()=="45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6"
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
