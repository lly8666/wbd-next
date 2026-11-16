#!/usr/bin/env bash
set -euo pipefail
sdk="$ANDROID_HOME"
out="out/apk"
src="experiments/android-root-probe/app"
mkdir -p "$out/classes" "$out/dex"
tools="$(find "$sdk/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n1)"
test -x "$tools/aapt2" && test -x "$tools/d8" && test -x "$tools/apksigner"
test -x "$tools/zipalign"
if [[ -f "$sdk/platforms/android-37/android.jar" ]];then
 jar="$sdk/platforms/android-37/android.jar";echo 37 >"$out/compile-api.txt"
elif [[ -f "$sdk/platforms/android-36/android.jar" ]];then
 jar="$sdk/platforms/android-36/android.jar";echo 36 >"$out/compile-api.txt"
else
 echo 'ENV_BLOCKED: No Android SDK API36/37' >"$out/blocked.txt";exit 2
fi
javac -encoding UTF-8 -source 8 -target 8 -classpath "$jar" -d "$out/classes" \
 "$src/src/org/wbdnext/rootprobe/"*.java
"$tools/d8" --min-api 28 --lib "$jar" --output "$out/dex" \
 $(find "$out/classes" -name '*.class')
"$tools/aapt2" link --manifest "$src/AndroidManifest.xml" -I "$jar" \
 --min-sdk-version 28 --target-sdk-version 37 -o "$out/unsigned.apk"
(cd "$out/dex";zip -q -j ../unsigned.apk classes.dex)
"$tools/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
keytool -genkeypair -alias probe -keystore "$out/temporary.jks" \
 -storepass android -keypass android -dname "CN=Disposable Probe,O=WBD,C=US" \
 -keyalg RSA -keysize 2048 -validity 2 -noprompt >/dev/null 2>&1
"$tools/apksigner" sign --ks "$out/temporary.jks" --ks-key-alias probe \
 --ks-pass pass:android --key-pass pass:android --out "$out/app-su.apk" "$out/aligned.apk"
"$tools/apksigner" verify "$out/app-su.apk"
"$tools/aapt" dump badging "$out/app-su.apk" >"$out/badging.txt"
grep "targetSdkVersion:'37'" "$out/badging.txt"
grep "sdkVersion:'28'" "$out/badging.txt"
echo "$GITHUB_SHA" >"$out/SOURCE"
( cd "$out"; sha256sum app-su.apk SOURCE badging.txt compile-api.txt >SHA256SUMS)
python3 - <<'PY'
import json,os,hashlib
from pathlib import Path
p=Path("out/apk")
d={"source":os.environ["GITHUB_SHA"],"min_sdk":28,"target_sdk":37,
 "compile_api":int((p/"compile-api.txt").read_text()),
 "apk_sha256":hashlib.sha256((p/"app-su.apk").read_bytes()).hexdigest(),
 "native_source":os.environ["GITHUB_SHA"],
 "scope":"real ordinary debug APK, not a Magisk/KernelSU installer"}
(p/"manifest.json").write_text(json.dumps(d,indent=2))
PY
( cd "$out";sha256sum manifest.json >>SHA256SUMS)
rm -f "$out/temporary.jks" "$out/unsigned.apk" "$out/aligned.apk"
