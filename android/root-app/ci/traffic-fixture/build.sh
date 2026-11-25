#!/usr/bin/env bash
set -euo pipefail
cd "${GITHUB_WORKSPACE:-$(pwd)}"
src=android/root-app/ci/traffic-fixture
out=out/android-traffic-fixture
mkdir -p "$out/host" "$out/classes" "$out/dex"
# Same ordinary socket code executes on the host and Android.
javac -source 8 -target 8 -d "$out/host" "$src/TrafficProbe.java"
python3 "$src/server.py" --bind 127.0.0.1 --port 0 --java-classes "$out/host" | tee "$out/host-smoke.txt"
sdk="${ANDROID_HOME:?Android SDK required}"
bt="$(find "$sdk/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n1)"
jar="$sdk/platforms/android-36/android.jar"
test -f "$jar" || jar="$sdk/platforms/android-35/android.jar"
javac -source 8 -target 8 -classpath "$jar" -d "$out/classes" "$src/TrafficProbe.java" "$src/TrafficInstrumentation.java"
"$bt/d8" --min-api 28 --lib "$jar" --output "$out/dex" $(find "$out/classes" -name '*.class')
"$bt/aapt2" link -I "$jar" --manifest "$src/AndroidManifest.xml" --min-sdk-version 28 --target-sdk-version 35 -o "$out/unsigned.apk"
(cd "$out/dex" && zip -q -j ../unsigned.apk classes.dex)
"$bt/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
keytool -genkeypair -alias traffic -keystore "$out/test.jks" -storepass android -keypass android -dname "CN=WBD Test Traffic" -keyalg RSA -keysize 2048 -validity 365 -noprompt >/dev/null 2>&1
"$bt/apksigner" sign --ks "$out/test.jks" --ks-key-alias traffic --ks-pass pass:android --key-pass pass:android --out "$out/traffic-fixture.apk" "$out/aligned.apk"
"$bt/apksigner" verify "$out/traffic-fixture.apk"
# A second independently installed ordinary UID, reusing the exact same dex.
sed -e 's/package="org.wbdnext.testtraffic"/package="org.wbdnext.testtraffic2"/' \
    -e 's/android:targetPackage="org.wbdnext.testtraffic"/android:targetPackage="org.wbdnext.testtraffic2"/' \
    -e 's/android:name="\.TrafficInstrumentation/android:name="org.wbdnext.testtraffic.TrafficInstrumentation/g' \
    "$src/AndroidManifest.xml" >"$out/secondary-manifest.xml"
"$bt/aapt2" link -I "$jar" --manifest "$out/secondary-manifest.xml" --min-sdk-version 28 --target-sdk-version 35 -o "$out/secondary-unsigned.apk"
(cd "$out/dex" && zip -q -j ../secondary-unsigned.apk classes.dex)
"$bt/zipalign" -f 4 "$out/secondary-unsigned.apk" "$out/secondary-aligned.apk"
"$bt/apksigner" sign --ks "$out/test.jks" --ks-key-alias traffic --ks-pass pass:android --key-pass pass:android --out "$out/traffic-fixture2.apk" "$out/secondary-aligned.apk"
"$bt/apksigner" verify "$out/traffic-fixture2.apk"
rm -f "$out/test.jks" "$out/unsigned.apk" "$out/aligned.apk" "$out/secondary-unsigned.apk" "$out/secondary-aligned.apk" "$out/secondary-manifest.xml"
