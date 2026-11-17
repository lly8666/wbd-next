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
