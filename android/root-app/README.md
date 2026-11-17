# Original Go/Rust Android ARM64 Root App — A5 experimental

This is a **separate Android package** `org.wbdnext.rootclient`, NOT the
historical `android/app` VpnService shell and not a KernelSU/Magisk installer.
It requests the user's **existing** su manager to launch the exact original
Go Android ARM64 client and the SAME source-locked Rust `libwbd_engine.so`.

## Honest build and device boundary

- `.github/workflows/android-root-product-a1.yml` builds Rust/Go AArch64
  first, then downloads those exact ELF files from its **same** source run.
  `ci/build-source-locked.sh` validates SOURCE, each SHA256, ELF machine183
  and 16KiB PT_LOAD alignment; it builds a Java/API35 ROOT APK with AOSP
  `javac`/`d8`/`aapt2`/`zipalign`/`apksigner` (no Gradle or JNI
  duplicate crypto code). The APK includes exactly one architecture's
  native binaries in signed `assets/native-arm64/`; the manifest is tested
  to contain **no** VpnService or BIND_VPN_SERVICE. The CI debug signing key
  is disposable, never a production release key.
- Activity selects a real `ConnectivityManager.Network`, validates the
  `getNetworkHandle()`, `LinkProperties` physical IPv4 and matching OS
  `NetworkInterface` ifindex/MTU, and asks for literal server IPv4,
  standard TLS SNI, original WBD credentials, offline 32-byte route key,
  optional CA PEM, and **one** non-system App UID. Network changes revoke
  the running root worker; there is no guessed default Network fallback.
- Account password/route key are app-private 0600 files passed by *path*
  to the original Go CLI's existing O_NOFOLLOW reader, NEVER command args
  or log text. The files are removed after the native process exits.
  The native ELF assets are streamed and SHA256 verified from the signed
  APK before being copied, using temporary names in the root-only 0700
  directory; executable staging never runs from Android app data.
- One `su -c` process performs POSIX-safe single-quoted arguments, an
  owner-PID + kernel starttime check **before replacing** any native ELF,
  and `exec` of the original Go binary with `LD_LIBRARY_PATH` pointing
  at the verified original Rust shared library. It retains no Java/JNI
  packet loop or fake authorization; original-Go real standard TLS/
  original lease/RAW/TUN/AEAD M4 alone can declare the native-ready event.
- `Stop` checks the *same exact* root-only process PID, kernel process
  starttime and `/proc/$pid/exe` before SIGTERM. The Go process then
  withdraws the authenticated one-UID routing journal and Stop/joins the
  original Rust M4 RX/TX threads; the foreground Service claims no
  completion until this original process has actually exited. No pkill
  wildcard and no SIGKILL success fiction.
- The UI's `NATIVE_M4_READY + ONE_UID_ROUTE_READBACK` state comes only
  from **both** original Go readiness log receipts. The UI expressly
  reports that real traffic is **not verified**, even at this stage.

## Current limitations

**NOT_RUN** on the user's Android16 ARM64 KSU phone: Root grant, Android
netd network routing, `ip -4 rule uidrange` support and `ip -j addr`
compatibility, actual FakeTCP+TLS/credential/lease to same original Linux
server, true bidirectional UDP/TCP, 65KiB M3 jumbo, physical switch and
Stop success, DNS, per-app discovery, split/global modes, IPv6, health,
power and performance. This APK is a first-connect **Normal/off** phase-A
prototype. Only one selected app UID is eligible for its private route,
not a systemwide service, DNS takeover or hotspot.

`main`, M0 registry/cursor, the existing Linux/Windows products and
the old Android VpnService shell are untouched. Only arm64-v8a is built,
signed or tested as an Android target.

Root launch hardening: no root filesystem mutations are allowed on a pre-existing symlink, foreign-owned directory, or directory lacking owner-only 0700 mode. Real stat UID/mode readback happens BEFORE native binary copy or chmod; active prior PID+kernel starttime checks precede ELF replacement.

## A6: selected physical Network events and source-locked host admission

The foreground Service now uses a single, per-session
`ConnectivityManager.registerNetworkCallback`, rather than a one-second
`postDelayed` network polling loop. Only loss/blocking or a scope-changing
`NetworkCapabilities` / `LinkProperties` callback for the **selected**
Network revokes its root worker; unrelated Wi-Fi/cellular events are ignored.
Callbacks consume their supplied state snapshots (no synchronous
ConnectivityManager lookups) and are unregistered after the owner exits.
The original Rust physical-scope check remains independent; this version
**stops**, rather than promising seamless failover, on physical-scope change.

Before su launch, the root owner rechecks the exact physical Network.
A Stop/loss during staged launch cancels a not-yet-started owner. For an
already started generation, one bounded cold Stop signal verifies its
unique random 128-bit generation token in root-owned `owner.pid`, its
kernel PID starttime and `/proc/PID/exe` before SIGTERM, so a newer
session cannot kill an older unrelated worker by stale pid-file identity.
Signal delivery is not counted as joined Go/Rust Stop success.

The same-source Actions APK job compiles and runs a **pure-Java
NetworkScopeGate unit test**. A separate `ubuntu-24.04-arm` job records
the actual ARM64 host architecture and KVM device permissions, but DOES
NOT boot Cuttlefish (a pinned matching guest image/host-tools set is
still not provisioned). A successful preflight Action does **not**
qualify Android, KernelSU or true Android↔Linux traffic: P2/P3/physical
remain NOT_RUN until an actual ARM64 guest and authorized runtime are
available. The previous macOS QEMU guest hang is retained as
ENV_BLOCKED historical evidence, not silently overwritten.

The exact Stop shell is now emitted by source-shared `RootStopCommand.build()` and its **production command string** is passed to a real host `sh -n` parser during Actions. This additional cold-control test catches syntax faults that the Android Java compiler alone cannot detect. Neither a successful parse nor APK build is a substitute for true rooted Android Stop.

Owner takeover protection now parses both the legacy two-field and new three-field root-only `owner.pid` records into three separate shell variables, so the generation token is not mistakenly folded into the kernel process starttime. This is checked by a host POSIX shell fixture in Actions; runtime Root safety remains Android-P3 NOT_RUN.

### A6 accepted CI evidence

[Actions #44056494256](https://github.com/lly8666/wbd-next/actions/runs/44056494256) at SOURCE `f7f142da2ad8e58365b7e36dd1ba6f734b32923c`: **5/5 jobs PASS**; Android ARM64 Go/Rust and signed Root APK BUILD_PASS, original Linux WBD server oracle PASS, JVM NetworkCallback gate 16 assertions, production Stop script POSIX sh -n 11 assertions, and old/new owner.pid parsing regression PASS. Host ARM64 has no accessible `/dev/kvm`, so Android guest/App Root/true network E2E remain **ENV_BLOCKED / NOT_RUN**. This does not authorize physical devices.

## A7: real installed-app picker (not manual arbitrary UID)

`RootClientActivity` queries current-user launcher apps using
`PackageManager.queryIntentActivities(MAIN+LAUNCHER)` and the **real**
`ApplicationInfo.uid`, deduplicates by package name and displays both
package and UID. Android11+ uses a narrowly scoped manifest `<queries>`
declaration, **not** `QUERY_ALL_PACKAGES`. System/root UID, the WBD
controller's own UID/package, and unlisted apps are excluded. The user
can refresh the installed-app snapshot. Unlaunchable or invisible packages
are intentionally not offered.

The signed APK's `START` action carries the selected package and exact
observed UID. The foreground Service reconfirms the association on Start
and again just before `su -c`, failing closed if the app was removed or
its UID changed. Selected package removal, replacement or component
changes send a protected Android broadcast to the Service, which requests
the already-defined generation-bound original Go/Rust Stop. The package
is never interpreted as an untrusted Go protocol argument or classified
per packet by Java.

**Shared Linux UID limitation:** several APKs can have the same UID;
the kernel's uidrange rule cannot separate them. This is disclosed in
the selector. The Java host policy test checks package syntax/UID
association, while the signed APK build checks narrow manifest queries.
Android runtime PackageManager visibility, dynamic package broadcasts,
real UID route readback and the complete Android↔Linux WBD link are
still P3 **NOT_RUN**.

## A8: actual bounded multi-UID Root route (Normal/off only)

Select **1–16 installed visible launcher packages**. A cold, canonical
selection resolves to **1–8 distinct sorted Android kernel UIDs**;
packages sharing an UID get ONE kernel route and cannot be separated
by a per-package policy. App UI, the foreground Service, and just before
the `su -c` launch all re-read PackageManager identity. Any selected
package removal/replacement/change requests an exact-generation Stop
for the whole group. No per-packet Java or extra native dataplane.

A single UID uses the existing original-Go `--android-route-uid`.
Two to eight use `--android-route-uids=...`; both remain Android-only
and mutually exclusive. Original Go standard TLS/credentials/verified
/32 lease and Rust M4 must succeed BEFORE Go grants the selected UIDs.
`rootjournal.NewGroup` uses the same owner.lock and journal pathname
as the legacy single UID, with a version-2 fsync'd receipt and exact
kernel readback of private table19842 and pref9600..9607. Each
UID rule is individually installed, rollback/recovery/Stop are bounded
and do not edit main/default netd routes. The legacy version-1 journal
can be recovered with strict matching ownership.

Current CI software proof is **NOT** actual Android ARM64 root / netd
routing / KSU E2E. DNS, split/direct modes, live multi-App packets and
physical switching remain NOT_RUN pending P2/P3/P5. 

## B2b source-locked CN geosite asset admission (not DNS takeover)

The Root APK build is now **dependent on two independently-qualified
jobs of the same Actions SOURCE**: the original ARM64 Go/Rust ELF and
the immutable authentic B2a v2fly geolocation-cn importer. The latter
must produce the exact 8,503-entry TXT, SHA256
`45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6`,
upstream provenance and MIT license. The signed no-VpnService APK
includes all three assets under `assets/native-arm64/`, and the
APK build opens its completed signed ZIP to verify those very bytes.

Android `NativePayload.stage()` checks signed provenance/source
commit/type counts, MIT license, streaming TXT SHA and exact size,
copies the TXT to private app-owned storage with mode 0600, then
passes its absolute pathname to the original Go
`--android-cn-geosite-file` cold-control argument. The original-Go
process itself opens the file with `O_NOFOLLOW`, rechecks 0600/regular
file/size, SHA and all four rule type counts, and logs only a
`CN8503_COLD_FILE_VERIFIED` receipt with
`dns_capture=NOT_CONNECTED`. Invalid/missing/mutated TXT fails before
the original protected TLS or UID route. The Go CLI flag is Android
client-only; existing Linux/Windows server and client mode defaults
do not change.

**Evidence boundary:** an APK build verifies real signed ZIP assets,
but Android16 ARM64 PackageManager access, SELinux/KSU access to
app-private 0600 and Go runtime cold receipt are NOT_RUN on a real
Android guest/phone. The Go cold verified list is currently **not
consumed by a DNS packet handler**. The system Resolver, physical
`android_setsocknetwork` DNS fd binding, inner Rust M4/TUN UDP/TCP53
capture/response and per-App actual data split remain NOT_CONNECTED.
No Java packet path, background downloads, VPN or FakeIP was added.


## A9 first ARM64 KernelSU device acceptance — safe diagnostic package

This is a first-run operator workflow, NOT a claim that an ARM64 Android
device or original Android-to-Linux WBD session has already passed.
The product is still only Android ARM64 Bionic original-Go + original-Rust
Normal/off, with both DNS capture gates disabled.

The signed Root APK now persists a bounded app-private receipt, and logs only
fixed allowlisted event names under the WBD_ROOT_DIAG tag. No username, app
package, server IP, owner token, original stdout, credential, TLS transcript,
route key, or individual UID is emitted to ADB or the ZIP. Native READY is
only observed after the original Go/Rust M4 and owned UID-route receipts;
sending SIGTERM is explicitly NOT counted as joined Stop.

On an authorized Android16 ARM64 KernelSU **device** (not the prior x86 KVM
NativeBridge guest), use Python 3 and adb from a computer. First examine
your own chosen signed artifact; CI uses a disposable debug-signing key,
and an existing installation signed with a different key may not upgrade.

Run an operator-controlled, single-session Start/Stop test:

```bash
python3 android/root-app/ci/device_first_run.py \
  --apk /path/to/wbd-root-arm64-debug.apk --install \
  --output out/device-acceptance/first-run
```

The script verifies local signed-archive ARM64 ELF/SOURCE byte integrity
(but does not itself verify APK signing), requires a kernel reported as
aarch64 and Android API36, checks for pre-existing WBD-owned routing rules,
then opens the original app Activity. The **user** selects physical Network,
installed App and own authorized Linux server, enters secrets on the phone,
presses Start, then Stop, and presses Enter at two CLI prompts. This is
deliberate: the script never enters credentials, asks for shell su, modifies
netd/routes, kills a process, or bypasses KernelSU Manager. Use --serial for
multiple connected devices. --install is the only opt-in device mutation;
omit it when the correct APK is already installed.

For read-only support collection without launching an app:

```bash
python3 android/root-app/ci/device_first_run.py --collect-only \
  --output out/device-acceptance/read-only
```

The resulting private acceptance-bundle.zip contains only structured
preflight, hashed WBD-owned rule state and whitelisted stage codes; it
intentionally excludes raw logcat/tombstones, user identifiers and secrets.
Do not assume arbitrary Android traffic, real TLS, joined Rust Stop or
system Resolver passed from a host build, Activity startup or this receipt.
A private-rule rollback PASS only means the inspected WBD-owned rules
are empty after the explicit user Stop **and** the Service cleanup event
was observed. If the route reader is unavailable, mark NOT_RUN; if private
rules remain, FAIL without attempting dangerous automatic repair.
The owner-controlled original-Go/Rust Stop and its existing route journal
remain the only production cleanup mechanism.

If the original app cannot start, use the read-only collection mode or
share the sanitized ZIP after examining it. Never share the Android
password/route key or raw logcat.
