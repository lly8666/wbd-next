# Original Go/Rust Android ARM64 Root App — A5 experimental

This is a **separate Android package** `org.wbdnext.rootclient`, NOT the
historical `android/app` VpnService shell and not a KernelSU/Magisk installer.
It requests the user's **existing** su manager to launch the exact original
Go Android ARM64 client and the SAME source-locked Rust `libwbd_engine.so`.

## A29 · Root Lite v2 简版测试 APK

本实验 APK 沿用 \`org.wbdnext.rootclient\` 和**原 Go + 原 Rust Normal/off**，桌面名称 \`WBD Root Lite v2 (TEST)\`。由同一个签名 APK 生成兼容旧 CI 名称 \`wbd-root-arm64-debug.apk\` 与直观的 \`wbd-root-lite-arm64-debug.apk\`，不是第二套模拟协议或 VPN。

本版把 main H2208 的 **RouteKey v2** 接到实际 Root Activity：输入 8–32 位 ASCII 英文字母/数字，离线 PBKDF2-HMAC-SHA256（4096 次、固定 v2 域盐）派生原 32 字节 route-key，**只**将派生 hex 写入现有 App 私有 \`wbd-route.secret\`，原 Go 仍使用 \`--route-key-hex-file\`/标准 TLS ClientHello/证书/用户名密码认证、原 Rust M4。另继续支持旧 64hex route-key，且不把它默默变成短口令。双方须显式采用同一个 v2 短 Key 或其派生 32B hex，旧 v1 240000 次无回落；8 位自选口令的真实安全性低于 256 位随机密钥，建议随机 24–32 位。

与 main Android Kotlin 已有辅助实现相同：应用 \`noBackupFilesDir\` 下以 \`SHA256(client\\0+SNI)\` 前12字节命名独立私有缓存，内容只有派生 32B hex 和 HMAC 校验值，不是明文短 Key 或账户密码；Mode 0600、AtomicFile，重复输入时先核对缓存而非重新 KDF。更换有效短 Key 明确轮换，格式坏则本地拒绝；原 Go 进程退出仍删除临时 \`wbd-route.secret\`，派生缓存直到清除 App 数据才删除。无在线 Key 协商/Go 逐包 Java 回调/隐式权限放宽。

UI 把进阶 KernelSU/TUN 一键自检放到默认折叠的“高级选项”，直观引导实体 Network → WBD server + SNI + 账户 → Key → START/STOP，并保留服务器/32 私有表 THROW 排除、默认普通App IPv4与可选单App、原 UID journal exact Stop、SAF脱敏TXT。**首次首选手动取消“默认普通App”并只选择一个实验 App**，该建议不改变现有默认路由行为。系统 DNS/IPv6/Root/system UID、Fixed/Game、Decoy server、Linux padding、VpnService 继续不支持。

同 SOURCE Host JVM 校验主线原 Go 的三个 v2 golden vectors、非法/轮换/损坏缓存与 hex 兼容；正式 APK DEX 需包含实际生产 KDF/缓存、源锁 Go/Rust ARM64 ELF/签名/SHA，独立原 Linux oracle。所有签名APK/Host PASS 不等于真机 FakeTCP SYNACK/TLS/32租约/M4/真实App UDP/TCP/Stop 已通过。本轮没有获授权连接个人手机/服务端或跑 KSU/TAP guest。

**测试版安装注意**：GitHub Actions 的调试签名证书每次生成，且 APK 包名相同，无法直接 \`adb install -r\` 覆盖上次版本。请自行先在旧版按 STOP，检查没有残留 KernelSU UID 私有路由，再卸载旧调试包并安装新的 Lite APK；卸载会清除派生缓存。


## B24 · Physical Ethernet + multi-App selection workflow

A real Android Ethernet/USB Ethernet `ConnectivityManager.Network` with a matched interface, IPv4, ifindex and MTU can now be explicitly selected as an original-Go/Rust underlay, alongside Wi-Fi and cellular. The foreground Service uses the **same** transport rule; loss or a true physical-scope change still stops the exact owned generation. UI refresh retains a selection only while those original Network/OS attributes remain identical. There is no automatic roaming, re-auth, or extra packet thread.

Selected-App mode now supports a local name/package/UID filter, preserves checked items hidden by filtering, and batch-selects matched visible Apps within the original 8-UID/16-package constraint. Search/selection only touches UI state; original-Go app routing remains a separate manual authenticated START with exact package/UID cold readback. Manifest still exposes only launcher-visible Apps, not `QUERY_ALL_PACKAGES`; invisible/nonlauncher applications are not claimed supported.

Same-SOURCE signed APK and Host checks qualify only BUILD/Host, not physical Ethernet, Android system DNS, actual App TCP/UDP delivery or performance.

## B25 · Save all valid shared-UID package selections

The original selected-App route already supports **up to 16 packages sharing at most 8 unique UIDs**. B22's optional saved connection preset incorrectly limited package entries to eight, dropping valid larger shared-UID selections after an Activity restart. B25 matches the original `SelectedAppGroup` limits in both the production preset writer and reader, validates package grammar via the existing `InstalledAppTarget`, and retains Android's exact cold PackageManager UID recheck before any new START. No new app routing permissions, network processing, Root action or automatic reconnect are introduced.

## B26 · Export/import ordinary connection settings across debug APKs; selected App discovery

The CI-signed debug APK uses a disposable signing key for each SOURCE. A fresh installation may require uninstalling the old package, which clears `noBackupFilesDir`. The Root Activity now offers **export and import through Android's document picker** for the actual production `RootConnectionSettings` (same B22/B25 codec), maximum 8KiB. This includes the server name, SNI, username, cipher, MTU, FEC/DNS modes and up to 16 selected package/UID identities. It deliberately **does not** export the password, RouteKey, TLS CA PEM, selected physical Network handle, native owner token or Root routing rule. Because exported settings include a username/server identity, choose the destination carefully. On import, only the cold form is restored and the selected App UIDs are rechecked against Android's currently visible installed packages; the user must re-enter credentials and explicitly START.

Selected-App discovery also includes packages exposing Android's regular **plain-text share** or **HTTPS-link open** activities, including some non-launcher apps. Manifest `<queries>` is deliberately narrow: there is **no** `QUERY_ALL_PACKAGES` and the capability does not extend to every non-launcher/system-invisible installed app. Fresh package/UID resolution is performed in the cold Service path and cannot be bypassed by an imported file. Search/chooser changes never touch an active original-Go/Rust owner.

Neither this work nor the prior DNS modes capture Android `netd` system resolver traffic. Existing UDP/53 logic only handles packets that actually enter the original Rust M4 TUN, and no root/system UID routes, new TLS layer or extra packet loop were added. All Android device E2E, system DNS interception and performance remain NOT_RUN without real evidence.

## B27 · LAN-only Wi-Fi / USB Ethernet physical underlay

A real Android Wi-Fi or USB Ethernet `Network` can carry working local IPv4 to a WBD server even without Android's `NET_CAPABILITY_INTERNET` flag. Previously both the Root App chooser and the foreground Service watcher incorrectly excluded those links, and its callback `NetworkRequest` only subscribed to Internet-capable Networks. The selection and its watcher now reuse the same **physical transport / not VPN** policy, while retaining all original kernel interface, ifindex, LinkProperties IPv4, MTU, generation and owned Stop checks. The callback explicitly subscribes to Wi-Fi, cellular and Ethernet, not only Internet-capable networks.

The dropdown labels LAN-only candidates as lacking the Android Internet capability; this is **not** an assertion that a WBD server is reachable. For a LAN-only link, enter the server's directly reachable **IPv4** and separately configure its TLS SNI, because the existing original-Go hostname bootstrap uses physical 223.5.5.5 and may be unavailable without internet. No automatic cellular fallback, broad Root rule, system DNS rewrite or additional hotpath worker is introduced. Changes of actual physical handle/ifindex/local IPv4/MTU still terminate the owned generation. B27 host/signed APK evidence is not a physical-device LAN or application delivery PASS.

## B28 · Use selected local Network DNS for a LAN WBD hostname before original Go TLS

An unvalidated/local-only physical Wi-Fi or Ethernet `Network` may have its own LAN DNS server and a WBD peer registered under a LAN domain. Original Go's public 223.5.5.5 pre-SYN bootstrap cannot resolve such names when there is no internet. The existing RootService worker therefore performs **one cold `Network.getAllByName(peer)` on the exact selected Android Network handle** (API 21+) for a DNS-name peer on an unvalidated link, selects an actual IPv4 A answer and passes it to the **same original Go `--peer-ip`** path. The original Go still owns FakeTCP SYN, standard TLS/route-key SessionID, credential admission, /32 lease, Rust M3/M4 and owned Stop. No connection is opened by Java, and no per-packet Go/Java callback is added.

When the selected Network resolver does not return an IPv4 address, the **existing original-Go physical 223.5.5.5 hostname bootstrap remains the fallback**, preserving behavior for mobile/hotspot networks that can reach the public resolver despite lacking Android's validation bit. An already-entered literal IPv4 bypasses DNS entirely; unchanged validated Internet links keep their original Go bootstrap behavior. If the peer is only reachable on a private LAN with no working resolver, use its literal IPv4 and a separately correct TLS SNI.

This is **only WBD's own pre-auth server bootstrap**. It does not capture or reroute Android system `netd` queries, implement global/private DNS, or prove physical WBD application delivery. Same-SOURCE signed APK and host testing are software gates; LAN DNS success and TCP/UDP E2E still require authorized actual-device evidence.

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
A rollback PASS requires the dedicated UID rules, table19842 routes
and wbdv40 TUN to be absent after explicit Stop **and** the Service
cleanup event to have been observed. A separate original-Go native
joined-Stop PASS requires the real V4_PUBLIC_NATIVE_STOP_DRAINED log
marker from native.Close(), original M4+UID readiness, user Stop and
native exit zero; sending SIGTERM alone can NEVER pass that gate.
An observed 132/139 original process exit is classified FAIL, not PASS. If the route reader is unavailable, mark NOT_RUN; if private
rules remain, FAIL without attempting dangerous automatic repair.
The owner-controlled original-Go/Rust Stop and its existing route journal
remain the only production cleanup mechanism.

If the original app cannot start, use the read-only collection mode or
share the sanitized ZIP after examining it. Never share the Android
password/route key or raw logcat.


## A10: 手机内一键 KernelSU/TUN/RAW/独立 UID 路由安全验收

**旧 Start 的 `Invalid server / TLS / credential / UID settings` 是预期的输入
拒绝**，不是物理 TUN/内核 Root 测试结果。Start 是真实原 Go
Normal/off 客户端：需要真实 WBD IPv4/域名、SNI、账号/密码、32-byte
route-key 的 64 个十六进制字符、1–16 已安装的真实目标 App；乱填不能
启动，因为不能伪造 TLS/authenticated lease。新版细分了表单错误，
但不放宽原协议凭据的安全校验。

**无服务端首次测试：** 安装 A10 SOURCE 对应的签名调试 APK，打开后不
填任何服务器设置，选择 Wi-Fi/蜂窝 Network，直接点击顶部
「一键自检 ARM64 / KSU / TUN / RAW / UID 路由及回滚（免服务器）」，
阅读临时内核规则说明后同意，在 KernelSU Manager 中授权该 App Root。
一次点击将顺序验证：

- `NativePayload.stage()` 对同一签名 APK 中**原始 ARM64 Go/Rust ELF
  与 CN8503 资产**执行 SOURCE/SHA256 门；测试专用 NDK Bionic ARM64
  C helper 另经 APK 内独立 SHA256 验证，**不替代原业务二进制**。
- 原始 Go `wbd-v4-client-arm64 --help` 实际从隔离 root-only
  目录启动（标注真实 SIGSEGV139/SIGILL132，绝不把加载测试认作TLS成功）。
- test-only C helper 真实调用 Linux `open(/dev/net/tun)`、
  `ioctl(TUNSETIFF IFF_TUN|IFF_NO_PI)`，查询真实ifindex，关闭 FD
  并确认不持久化；真实 `AF_PACKET/SOCK_RAW` 在所选物理接口 bind
  后立即关闭；`SO_BINDTODEVICE` socket 仅设置选定接口，不发送包。
- 在隔离root shell里尝试 **只针对本APK UID** 的
  `pref 9699 uidrange APP_UID-APP_UID lookup 19843` 和
  `192.0.2.1/32 dev lo table 19843`。它只指向IANA文档测试IPv4
  地址，既不接管系统默认网关，也不使用正常WBD
  table19842/pref9600..9607或目标App UID。真实内核安装/readback，
  `trap EXIT` 使用完全匹配的规则和路由撤销，再被动readback。
  预存规则/路由占位直接拒绝覆盖；不执行自动修复已有网络状态。
- 所有原始root/stdout/凭据/IP/UID被过滤，UI只显示固定
  PASS/FAIL/NOT_RUN阶段码，支持长按或「复制一键自检结果」。

**风险声明**：这是经用户按钮授权的短暂原生内核测试，但进程被
`SIGKILL`、设备断电或内核异常时，POSIX清理陷阱不是绝对保证，
必须检查 `ROUTE_ROLLBACK_PASS`；若FAIL，停止重复测试并检查专用
table19843/pref9699。普通 shell KernelSU授权不代表原 Go/Rust 在
厂商 SELinux 下必定可工作。

**严格未测**：无真实服务器凭据时，原Go真实TLS/authenticated lease、
原 Rust M3/M4双向应用UDP/TCP、生产App选定UID转发以及Android
system Resolver/物理/tunnel DNS接管仍是 `NOT_RUN`。双DNS冷开关
继续false。绝不将模拟TUN创建+策略readback称为真实隧道成功。
正式产品仍保持原Go/Rust ABI/data plane，不增加JNI/Java逐包循环、
VpnService/FakeIP。

**签名注意**：Actions生成一次性调试签名密钥，若旧APK由另一套密钥
签名，Android不能直接覆盖升级。须**自己备份需要的数据后**
卸载旧版 `org.wbdnext.rootclient` 再装新的调试APK；卸载会擦除本
App 私有配置/密钥，切勿在原业务正在运行时卸载，也不能使用
`adb install -r` 绕过签名校验。


## A11 — 真正本APK UID UDP包进入临时TUN（无服务器、原协议不变）

A10 用户在本人真 ARM64 KernelSU 手机上报告 ROOT、原Go ELF帮助、
TUN创建/销毁、RAW、物理Network、私有UID规则和回滚全部PASS，
但它证明的是**规则安装及内核能力**，不是包真的进TUN。

新 A11 在**同一个一键自检按钮**后自动追加隔离的真实包检验
（只在 A10 的 Root/TUN/Route UID/Rollback 四项全PASS时）。
由本 Android APK 进程的真正Linux UID经未绑定Network的
`DatagramSocket`发送单个固定 `WBD_A11_TUN_UID` UDP payload
给 **仅用于文档的 TEST-NET-1 IPv4 `192.0.2.1:43999`**。
原生调试helper有界9.5秒持有非持久`wbdst11` TUN FD，
内核独立路由表19843只有此/32路由和本 APK 精确 UID pref9699；
在`ip route get ... uid APK_UID`读回确定`wbdst11`之前**禁止发送**。
C在真正的TUN FD里逐字节检验原IPv4/UDP包内容，不造数据面、
不经任意互联网服务器，不读取任何应用原始流量，原真实Go/Rust
M3/M4协议不做替代。流程结束/失败陷阱先撤规则和路由再join helper
关闭TUN，并读回3种资源是否残留。

只有出现 `A11_UID_TUN_PACKET_PASS`、`A11_UID_TUN_ROLLBACK_PASS`
与 `REAL_APP_UID_TO_TEMP_TUN_PACKET=PASS`，才可以说在本人设备上
真实本APK UID 的单包进入了TUN（仍不是别的用户App、
生产WBD原Rust M4、TLS/租约或系统DNS的PASS）。

如果 `A11_UID_ROUTE_LOOKUP_FAIL`，意味着当前 Android kernel
的按UID路由读回接口可能不支持/拒绝该命令，测试将安全不发包；
如果 `A11_UID_TUN_PACKET_FAIL`，则说明Java UDP发送未被此
独立TUN按固定验证条件捕获，**不应宣称路由劫持成功**。
任何`A11_UID_TUN_ROLLBACK_FAIL`必须停止重复测试并人工核查
pref9699/table19843/wbdst11。系统DNS双门仍关闭、原WBD
服务器TLS/Rust真实转发/Stop独立NOT_RUN。

此自检使用单独的测试VIP、测试UID和权限，**绝不**使用
用户填写的WBD服务器地址或密码；升级 Actions 一次性签名
调试APK如果报签名冲突，用户须备份且确认WBD已停止后手动卸旧版。

## A12: 真机 A11 路由阶段失败的分层回执

A11 用户真机重复得到 A10 原 Go ELF / TUN / RAW / 物理网络 / UID
loopback规则+rollback PASS；但 `A11_UID_TUN_ROUTE_FAIL`
和 `A11_UID_TUN_ROLLBACK_PASS`同时出现，表示隔离 TUN 路由流程
**未完成**、已清理、Java没有发 UDP 测试包。
`A11_ROOT_CHILD_EXIT_NONZERO`是root测试Shell按设计退场，
不是原Go ELF139、也不是原Rust M4崩溃。

A12 在同一个一键按钮后增加固定的 `A12_*` 失败收据，
严格区分 TUN 网卡消失、路由添加、UID rule添加、rule读回、
路由表读回。路由/规则添加失败时输出固定
`ERR_EINVAL`、`ERR_EPERM`、`ERR_DEVICE`、`ERR_EXISTS`
或`ERR_OTHER`。只在root专用0700目录临时读取错误，
从不向Java/ADB显示 IP、UID、原始stderr、账号或原生包。
保留 A11 旧失败码、精确 `pref 9699/table19843` + `wbdst11`
回滚、未验证真实kernel UID选路绝不发包，**不自动尝试危险替代路由**。

安装 A12 后点同一个按钮，把 **A12_* + A11_* + rollback**
原样复制回来即可定位下一步。此版本仍不做无服务器原 WBD
TLS/租约/Rust M4数据E2E或系统DNS接管。

## A26: original ARM64 APK ↔ Go/Rust wiring, Actions-only

The production `RootClientService` now obtains original Go Normal/off
argv from `OriginalGoCommandArgs.build(...)`, a pure Java implementation
also executed in Host JVM tests (not a duplicate mock). Tests cover exact
Network handle/IP/interface flags, IPv4 vs DNS bootstrap, SNI/optional CA,
app-private password/route-key *file paths*, one/many/all verified App UID
routes, protected auto-/32, outer MTU 1460, no outer repair and invalid
inputs. No alternative TLS or Rust M4 implementation is introduced.

After building the **actual signed ARM64 APK**, Actions confirms
`classes.dex` includes the production argv builder, RootService and exact
Stop class; signed Go/Rust ELF SHA/source manifests, ABI and original Go
`libwbd_engine.so` dynamic dependency agree. The `wiring-receipt.json`
is uploaded with the disposable-debug-signed APK.

x86 KSU/TAP guest jobs are now **manual workflow_dispatch opt-in only**,
not part of automatic APK wiring checks. Host and APK build gates are not
a device launch, real FakeTCP/TLS/lease, kernel UID routing, data or Stop
test. These all remain NOT_RUN on this new SOURCE; historical A25 evidence
is retained separately.

## A27 — Default app IPv4 scope, server /32 bypass and phone-safe diagnostics

The default UI ON covers ONLY ordinary Android App IPv4 UID ranges:
AppID 10000–19999 in 20 supported Android users, excluding the WBD
controller and recognized KernelSU Manager AppIDs. Root, Android system
services/isolated UIDs, IPv6, system DNS, hotspot, USB, CLAT and all-device
kill-switch semantics are NOT covered. No VpnService is used.

For the default all-app mode the original Go cold controller now includes
the actual resolved original server IPv4 in a private-table root journal.
After genuine authentication/lease/M4, it adds a server-host /32 THROW
route in the same owned routing table 19842, reads it back, and ONLY THEN
installs ordinary App UID rules. This prevents that destination from
re-entering the WBD TUN. Owned Stop reverses exact UID, THROW, default and
journal; old v3 app route journal is exact-owner recoverable to v4.
No global default routing, system DNS or SELinux is modified. The next
Android netd routing rule and true physical egress are NOT device-qualified,
so a THROW readback is NOT proof of direct server traffic. The new
destination exception applies to default all-app, not optional one/multi
UID policies.

First genuine phone failures are most likely staged:
(1) KSU Manager detection, permissions, FGS/API35, selected physical
Network handle/ifindex/MTU; (2) su denial, SELinux, root 0700 staging,
original Bionic Go ELF/Rust shared library; (3) TUN/RAW socket privileges,
bound physical egress, original FakeTCP SYN sendto but no genuine SYNACK
or an untrusted RST; (4) real server raw socket, route key, TLS certificate
trust/SNI/password, protected /32 lease; (5) Rust M4 readiness; (6) ip tool
support for THROW /32 and uidrange, Android netd precedence, table19842
conflicts and route journal; (7) exact-owned PID/generation Stop and any
stale rules after abrupt process death. These are hypotheses to classify,
not claimed Android failures or passed device checks.

The new APK button 导出脱敏排障 TXT opens Android's standard
ACTION_CREATE_DOCUMENT file picker. It saves a bounded plain text report
containing ONLY allowlisted 13-digit time+fixed original-Go/Root stage
enums, the signed APK SOURCE SHA and Android API level, plus a
last-session category and private-FIB server-THROW observed/not-observed.
It NEVER reads logcat, raw native stdout, root journals, TLS transcript,
app names, UID ranges, passwords, keys, server IP or user secrets. It
does not request Root, send data or modify routes. After a failure or
Stop, choose this button, save the TXT, and share it explicitly.

Actions run host original-Go route policy tests including THROW ordering,
fail-closed rollback, foreign FIB rejection, v3→v4 recovery and owned
Stop, and host JVM tests for the SAME production diagnostic exporter
including injected secret-line filtering and bounded rollover. The signed
APK DEX must contain the exporter. This scope excludes emulator network
binding, phone installation, actual netd/TLS/M4/data and device Stop.

## A30 · 真实 Android API36 PRE_TUN / EXIT_1 安全分段诊断

用户用 A29 `6bcdbc6c...` 的测试版在 API36 获得 **`ROOT_OR_NATIVE_EXIT_1 after PRE_TUN`**，并主动上传固定阶段报告。 `ROOT_PROCESS_LAUNCHED`→`ROOT_PROCESS_EXIT_NONZERO` 间隔 **341ms**；有真实APK SOURCE验签、网络和UID配置检查、Java创建 `su` 子进程的证据，**但不证明 Root 授权、su shell 实际执行、ELF 链接、原 Go 解析、TUN 或原 Linux 联机**。 `OWNER_CLEANUP_FINISHED` 为Java清理，不代表内核 owned Stop；`server_ip_exclusion_readback=NOT_OBSERVED` 也是 pre-TUN 阶段的预期未观察项，而不是服务器/32旁路本身损坏的证据。

A30 在**同一**真实 root shell 和原 Bionic Go `Run` 入口中添加仅常量的阶段标记，顺序区分 `su` 是否实际进入，EUID0，私有目录/旧PID，真实 Go+Rust staging，owner pid 写入，`exec` 请求，原 Go 入口/参数拒绝/成功/实际物理接口/TUN open前后。生产 RootService 只读取完整固定标记并写到 app-private 原 `RootDiagnosticReceipt.Event`（13位毫秒），不保存原生输出、错误正文、PID、UID、IP、密码或密钥。报告对新V2 session按最后真观察到的阶段解释早退；对旧V1报告**不会倒推成 su 或 Go 失败**。此诊断本身不是设备的Root/TUN、内核路由、真正TLS/M4/应用TCP UDP或Stop的PASS。

完成同源 Actions、签名APK、原Linux Host oracle之后，用户可选择自行安装新调试版，失败一次通过原有“导出脱敏排障 TXT”发送新阶段报告。由于每批debug签名不同，升级前保存旧报告、检查旧Root进程和私有路由确实已停止；不要直接删除 `owner.pid`、不要 `ip rule flush`、不反复点击START。未经授权本任务不操作实体手机或服务器，也不运行 hosted TAP/KSU模拟器。


## A31 API36 原 Go 参数解析拒绝：固定分类诊断

用户 A30 真机收据已经证明 KernelSU EUID0 与原 ARM64 Go 入口真正执行，却在原 Go `parse(role,args)` 中返回拒绝；尚未调用TUN/RAW。A31不放宽安全校验，而在真正 Go 失败点输出13种脱敏固定类别（CLI标志、密码文件、RouteKey文件/内容、安装ID、CN规则、TLS CA、全App排除、Android Network scope、服务器地址、冷必填参数、模式策略及OTHER）。Android SAF TXT仍只收枚举，不保存原始Go错误正文或私人内容。旧版泛拒绝报告保持正确。新签名版 Host/构建通过不意味着真机parse问题已修复；用户可在确认旧 Root 会话/UID 路由安全停止并保留旧报告后，自行安装并保留原设置尝试一次，导出脱敏TXT。不清所有系统路由，不重设服务器/密钥。

## A32 · 修复真实 API36 PASSWORD_FILE 冷启动

用户提供的 A31 真机固定收据已证明 Root/原 Go 可运行，原 Go `parse` 在 `--password-file` 失败，未触碰TUN/TLS。Android `Context.MODE_PRIVATE` 并不保证原 Go 要求的 0600：AOSP默认文件权限可能是0660，而原Go O_NOFOLLOW/fstat明确拒绝所有组读写位。旧版密码和RouteKey使用同一Android写法；如果只修密码，将很可能马上卡到RouteKey。

A32将密码、RouteKey及可选CA统一使用 Android `Os.open(O_NOFOLLOW|O_CLOEXEC|O_CREAT|O_TRUNC,0600)`，同一fd强制 `fchmod(0600)`、同步并 `fstat` 读回，校验App所有者、唯一硬链、文件类型与大小；RootService请求 `su` 前再次 `lstat` 检查。仅新固定枚举 `APP_PRIVATE_CREDENTIALS_0600_VERIFIED`/ `APP_PRIVATE_CREDENTIALS_UNSAFE` 进入原SAF脱敏TXT。Linux原Go严格校验/标准TLS/UID路由/Stop均未放宽。宿主使用真实POSIX文件的0660/0640/0644/错UID/symlink/hardlink/64hex回归，签名APK内生产类/原ELF须同SOURCE核验。用户实机st_mode及后续解析结果待新TXT确认，不运行用户设备/模拟NIC。
