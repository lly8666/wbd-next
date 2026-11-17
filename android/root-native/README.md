# Android ARM64 Root product-native adapter (A2)

Production adapter boundary, **not** the existing probe or a connectable APK.

- `android_abi.c`: compile-time Bionic ifreq/TUN/socket ABI gates for Android64.
- `crates/wbd-platform/src/android_root_io.rs`: owned TUN FD handoff; A2
  strictly bounded Bionic RAW IPv4 TX and tuple-filtered RX socket owners,
  tied to the caller's exact Android Network/ifindex/physical MTU/generation.
  TX requires a complete packet built by the original Rust owner and its
  approved route budget, RX remains untrusted until original AEAD/replay.
  No unbound fallback, global fwmark/UID bypass, TUN creation or route mutation.
  The A2 handoff binds the original authenticated Rust Entry to this exact
  Network and owns both RAW FDs and duplicated TUN FD; the live M4 loop
  has **not** been ported and no DATA is sent/received by these handles.
- `build-source-locked.sh`: NDK cross-build of **actual shared `wbd-engine`**
  and pinned original-Go product CLI overlay using Android GOOS/CGO, excluding
  native ISA-L to keep Normal/off first-connect unblocked.
- `.github/workflows/android-root-product-a1.yml`: source-locked, hash-checked
  build-only Action; genuine TLS/lease/real server delivery and Stop are NOT_RUN.

**Next A2:** wire original-Go FakeTCP TLS/authenticated cold handoff, selected
physical Android Network and Rust authenticated M4 raw/TUN workloop; A3 then
test Android16 genuine KSU App ↔ source-locked Linux WBD server, real TCP/UDP.
No VpnService, fake TLS, new protocol or probe-derived production success.

- `r0/go_overlay/internal/realityfront/bridge_v4_android_network_android.go`:
  Android-only original Go post-TLS, post-Detach physical Network/MTU bridge.
  The Linux twin rejects Android-only values and preserves its existing path.
  The root app must supply a real Network handle; none is invented here.

- A2 borrowed-I/O safety: existing `wbd-platform::r1::BorrowFence` guards
  every synchronous RAW/TUN syscall. Original Entry Stop refuses to close an
  FD with outstanding driver loans. A new ARM64-only original M4 Normal/off
  worker now calls the same M1/M3 owner; Stop signals two kernel eventfds,
  synchronously joins RX/TX, then retires the original owner and FDs.
  **Source compilation is not actual device I/O or join evidence.**

- Before the first original Go FakeTCP SYN/TLS ClientHello, Android root cold
  CLI requires `--android-network-handle`; `faketcp` uses libandroid
  per-socket `android_setsocknetwork` plus exact SO_BINDTODEVICE on its
  existing IPPROTO_RAW sender, while keeping original AF_PACKET RX. This
  does not make existing Linux CLI TUN setup Android production routing.

## 2026-11-17 ARM64-only target

Only Android arm64-v8a (aarch64-linux-android / Go arm64) is developed,
compiled, packaged and qualified. Historical Android x86 stages are archived
but NOT target gates. Existing Linux/Windows x86 code and tests are unaffected.

Large cross-layer SOURCE batches combine original Go cold control, shared Rust
M1/M3, actual Bionic RAW/TUN, borrowed-FD Stop and catalog/governance.
Independent code paths are prepared concurrently, then integrated once and
validated by one ARM64 Actions run. No fake M4 ABI to force the link green.

## ARM64 A2 original M4 worker batch

`crates/wbd-engine/src/v4_android_original_m4.rs` is a **real**
ARM64-only pair of native readiness threads (not placeholder C symbols):
- Original M1 slab and single M3 replay/AEAD/Normal LINK, strict checksum/
  tuple original carrier and verified Go client /32 before TUN delivery.
- Original FrozenRecord/PN + shared IPv4/TCP writer on bound RAW socket;
  no Go/Java packet callbacks or auto-resend of an uncertain send.
- Original canonical encrypted HealthClock kind0 from the very same Rust
  owner: only native AEAD+unique PN+typed control can refresh peer activity.
- Physical Network MTU and ifindex recheck, fail-closed on changes.
- One eventfd per worker, no 10ms idle spinner; Stop signals both, joins
  both BEFORE original crypto retirement, checks original BorrowFence and
  removes owned RAW/TUN FDs only after drained.

**Remaining blockers**: source-locked ARM64 Go *full* FEC/Game/M2 linker
has missing genuine original modes; ARM64 health and Stop are not yet
device-executed. One source lock and static M4 symbol check CANNOT be
promoted into real WBD connectivity, multi-IP jumbo delivery, finished
root UI/controller, FEC/Game or Android16 KSU acceptance.

## ARM64 Normal/off original-Go product edition

Source-locked Go now uses original `wbd_v4_embedded_go` **without**
`wbd_v4_fec2_product`; the repository already provides disabled
Fixed/Auto/Game branches which explicitly reject unsupported modes.
No placeholder FEC/Game C symbols, no second TLS/AEAD or fake M2.

Original Android Normal/off `stage/readback` verifies this same
Go-authenticated nonzero epoch, feature3 and increasing revision. A green
Rust ARM64 ELF still does NOT mean a linked Go executable or real device.

The existing non-FEC original Go server adoption signature names a
`V4LinuxGameAuthenticatedLane` whose definition originally lives only in
the mature Game build. Android's Normal/off product edition now supplies
only that original protected **Normal** type and a strict policy reader,
requiring real ColdSnapshot/commit/association and refusing every FEC/Game
policy. This is type-level source closure, NOT a stub Game runtime.

Android's existing Normal/off CLI also needs the exact original FakeTCP
detached final-TLS-ACK bounded cold retry, which used to live behind
Game's optional Go build tag. The Android-only no-FEC file retains the
**identical verified ACK behavior**, while the original Linux file is
selected unchanged on Linux and all Game calls fail closed.

The Android Native original Go client /32 binding is now genuinely
exported: an accidental Linux-only cfg had excluded the existing
verified-lease FFI. The Android MTU readback uses the exact selected
physical RAW socket and the SAME Rust FrameBudget's peer MSS/record/LINK
deductions, never the default unbound Android Network.

## ARM64 A3: bounded real original-Go Normal/off link

The original Linux CGo control bridge is unchanged for Linux (`!android`
build selection). Android's separately compiled original-Go control adapter
references **only** genuine Rust TLS/lease/M1/M3/M4/Health/Stop and real
physical MTU functions; optional unfinished M2/Fixed/FEC/Game/shared-TUN/
Linux diagnostics fail closed as unsupported Go capabilities, never native
placeholder exports. Original authenticated Linux behavior is preserved.

Android first connect uses its owned native RAW/TUN generation without
pretending to have Linux's process-shared tun or A/B promotion. Only feature3/
Normal/off, verified auto-/32 and outer repair OFF are currently allowed.

The bounded native RX worker reuses one M1-ready Vec across all raw packets;
thread CPU telemetry samples Bionic CLOCK_THREAD_CPUTIME_ID per readiness
turn rather than per packet, reporting real worker CPU only.

## A3 original M3 full-IP TUN readv and bounded jumbo TX

The Android original M4 reads one COMPLETE TUN IPv4 datagram using two
kernel iovecs under the existing BorrowFence: small traffic goes straight
into its original M1 slab (no extra copy/Vec); jumbo overflow goes into a
one-time preallocated 65KiB TX worker scratch. The original authenticated
client /32 source and exact IPv4 length are checked BEFORE original PN seal.

The ORIGINAL M3 `LinkPacketPlan` issues its unchanged LINK20 bytes directly
to loaned original M1 slabs (including LINK_MAGIC escape), for up to eight
definitely kernel-copied immutable FrozenRecords per work turn. One packet
ID, generation, stride and physical MTU are fixed. On ambiguous send,
Stop or scope change the remaining fragment plan is retired, never
regenerated with an already-consumed PN. Native Health remains fair.

CI also runs a pure M3 LINK20 byte-oracle independently of the Android ARM64
build; neither the oracle nor the cross-compiled ELF claims device
execution, real network data delivery or Root permissions.

## A4: authenticated single-app UID route (not a VPN Service)

Optional Android-only `--android-route-uid=<non-system App UID>`
grants ONE application a kernel rule in private IPv4 table 19842,
priority 9600, only AFTER original Go verified TLS/auto /32, actual
TUN address readback, original Rust M4 loop start and FakeTCP handoff.
Default UID 0 changes no routing; it never captures the native root
Go process or other apps. No global main route, DNS, fwmark or VpnService.

Root-only 0700 directory, 0600 O_EXCL/O_NOFOLLOW fsync'd journal and
nonblocking cross-process flock preserve exact UID/TUN ownership.
First remove the app UID rule, then private route, verify both absent,
unlink/fsync journal and release lock BEFORE original Rust Stop/join.
Crashes recover exactly those kernel objects; live old owner cannot
be preempted. Separate real native underlay-invalid terminal flag
withdraws the route without forging an authenticated-peer dead flag.

Pure Go fake-kernel state-machine tests run before ARM64 native CGo gate.
Neither source compilation nor host tests prove real Android KSU,
iproute2 uidrange, TLS/lease, kernel TUN I/O or Root application UI.

## A5 separate original Go/Rust Android Root application

`android/root-app` is an independent Java APK, NOT the historical
`android/app` VpnService. Physical Networks are selected using real
ConnectivityManager handles/LinkProperties and kernel interface
readback. Private original-Go credential/key files never go in argv.
CI bundles the exact same-source ARM64 original Go ELF and Rust .so
into a signed SDK35 APK, with SHA/ELF/16KiB and no-VpnService checks.
The Root Service issues SIGTERM only to the exact live PID/starttime/exe
and waits for the original Go/Native owner to actually exit. All Android
phone traffic and device root permission remain NOT_RUN.

## B1 ordinary DNS wire: real host UDP/TCP test, not Android interception

An original-Go source-locked `internal/v4productcli/dnsnative` package
implements no-FakeIP DNS question parsing, actual UDP DNS request/answer,
and TCP retry **only to the same upstream and route** after TC=1.
Configured production endpoints are **223.5.5.5:53** (physical CN DNS)
and **1.1.1.1:53** (WBD tunnel DNS). Split-enabled queries use the
original QNAME with caller-provided CNMatch; split off sends ordinary
queries to tunnel DNS. Bootstrap domain queries always use physical CN.
There is no fallback to the other upstream or implicit OS DNS.

Every socket uses an injected path-aware DialFunc; nil fails closed.
The component itself never opens an unbound net.Dialer. Strict DNS
ID/question checks, bounded wire sizes, 256-entry positive TTL cache,
ID rewriting, 64 independent in-flight cap and identical query
coalescing use no background timers. A parallel Actions job runs
**actual UDP and TCP loopback responders on ephemeral ports**, not fake
DNS strings. The original ARM64 build installs the same package into
the pinned Go donor and cross-compiles an Android ARM64 test ELF.

**Not yet integrated:** Android system resolver interception, actual
physical ConnectivityManager socket binding, original Go/Rust M4 TUN
UDP/TCP53 capture, production geosite CN classifier, live direct/tunnel
DNS and Private DNS/CLAT. Test success is host-wire qualification,
NOT Android P2/P3 E2E or true UDP port 53. A8 route remains unchanged.

## B2 pinned 8,503-entry CN geosite matcher (host source qualification)

The B1 Go `dnsnative` package now contains `CNRules` and
`NewPinnedCNResolver`: it accepts **only** the immutable, authentic
`v2fly/domain-list-community` geolocation-cn snapshot from pinned
upstream commit `41504eae2a11f305fe88cfc605cf6c105a80bf5a`,
after the original repository importer expands includes, attribute
filters and affiliation entries. It checks the complete snapshot
SHA256 `45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6`
and exact counts: 8,503 distinct entries (8,431 suffix/domain, 69
exact/full, 3 regexp, 0 keyword). All four type semantics have their
own implementation; a regexp cannot silently be converted to suffix.
The matcher runs only on normalized **original DNS QNAME**, not DATA
packets or returned A addresses. Full DNS answer is unchanged; no
FakeIP.

The dedicated B2 host job downloads precisely the pinned upstream ZIP,
runs the previous proven deterministic Python importer, checks complete
type counts, exact TXT SHA and included MIT license, and tests the
**real production Go matcher** with the genuine snapshot against real
local UDP/TCP DNS socket responders. Rule decoding is bounded to 6MB,
uses an exact checksum, validates type, labels, ordering and counts,
and rejects partial/mutated rules. Enabling CN DNS split without a
fully supplied matcher now fails closed rather than silently sending
all CN traffic to tunnel DNS. No fallback endpoints or background
phone downloads.

The snapshot remains a verified build/test **artifact**, not yet
bundled in the signed Root APK or loaded by the live original Go
client. CN DNS is still NOT_CONNECTED to Android netd Resolver,
physical ConnectivityManager network-bound DNS sockets, Rust M4/TUN
capture or the installed APK; the Android16 ARM64 P2/P3 KVM guest is
still blocked. Do not equate B2 host proof with device DNS routing.

## B2b signed Geosite to original Go cold-control chain

The signed Root APK only builds after B2's independent immutable
geolocation-cn importer job and the pinned original Go/Rust ARM64
native job both succeed for the identical source SHA. The first job
creates TXT+MIT license+provenance and a JSON receipt; the APK
build verifies its source/run and all hashes, then signs the TXT in
`assets/native-arm64/`. The Android App rehashes TXT before copying
it to 0600 private app data; the REAL original-Go CLI now accepts
`--android-cn-geosite-file` **only on Android**, and its pure-Go
`dnsnative.ReadPinnedCNFile` checks owner-only regular mode,
`O_NOFOLLOW`, bounded size, exact v2fly pinned SHA and 8,503
typed rules. Host Go tests exercise valid copy, world readable,
symlink, modified bytes and directory rejection. Go emits a
distinct cold file checksum receipt, expressly marked
`dns_capture=NOT_CONNECTED`.

This is not a system DNS listener, Android system resolver rewrite,
tunnel DNS socket routing, or P2/P3 native Root execution proof.
All direct/tunnel DNS packet capture, KernelSU runtime and physical
network bind gates remain separate and NOT_RUN.

## B2c1: actual Android netd physical DNS socket binding (cold scope)

Source-locked original Go now constructs a scoped **physical-only**
`dnsnative.NewAndroidPhysicalDNSDialer` from the exact
`ConnectivityManager.Network.getNetworkHandle()`, original interface
name, kernel ifindex and MTU, and observed `LinkProperties` IPv4.
On Android Bionic CGO, each new **UDP or TCP** DNS socket uses
`net.Dialer.ControlContext` before connect to call the same
`android_setsocknetwork` NDK API used by original-Go FakeTCP RAW,
plus `SO_BINDTODEVICE` and device name readback. The source IPv4 is
explicitly selected; no implicit resolver/default route/IPv6, and only
the fixed physical `223.5.5.5:53` endpoint and `Physical` path
are accepted. The code revalidates actual ifindex/MTU/IP before
and after connect. Failed mark/readback or selected network change
closes the socket without cross-upstream fallback.

This is a **real socket implementation, not an Android packet
interceptor**. The original Go Android cold owner constructs this
physical-only dialer after validating its selected Network; it
does not call `Resolve` or send DNS data yet. There is no tunnel
dialer, local DNS listener, shared Rust M4/TUN UDP/TCP53 extraction,
system netd Resolver redirect or direct/Global/split IP rule change
in B2c1.

Dedicated Actions exercises actual Linux kernel loopback UDP,
TC→same-endpoint TCP, source local IP and per-socket
`ControlContext` callback order, deliberately failed mark with
zero transmitted UDP packets, invalid handle/index/MTU/IP, wrong
endpoint and Tunnel rejection. These tests use an injected **host
callback** and are not Android `android_setsocknetwork` runtime
evidence. The already pinned original ARM64 Android CGO build
must link the NDK implementation called by the cold original-Go
client; a separate Android CGO=0 test ELF only builds the
fail-closed stub. Neither counts as P2/P3 Android guest/root execution.

## B2c2a: genuine original Rust M4 ONE-TUN IPv4 DNS53 observer

The authenticated Android ARM64 original Rust `tun_worker` remains the
**only** owner of `AndroidOwnedTun::read_ip_scatter`. After the original
leased-/32/IPv4 validation, it inspects the kernel-filled, unmodified M1
slab for strictly bounded IPv4 UDP DNS question port 53 and for a TCP
destination-port-53 **flow candidate**. No additional TUN read,
buffer copy, Go/Java callback, timer or extra worker is introduced.
The qualified packet is still passed **unchanged** into the original
Rust M1/M3 authenticated AEAD/PN worker. Jumbo/partial-scatter and
malformed datagrams receive a bounded metadata-only diagnostic,
not an unqualified DNS reply or redirection. For TCP, observing a
SYN does **not** claim DNS TCP stream reassembly.

The Android Rust ELF exposes a readonly stats-only original-owner
`wbd_m0_embedded_go_loop_dns_ingress_observed` C ABI: qualified UDP,
TCP flow candidates, incomplete candidates, and
`hijack_enabled=0`. This does not alter the old Go ABI methods or
enable any DNS effect. Host Rust tests exercise actual constructed
IPv4/UDP/TCP53 wire bytes and adversarial length, fragment, name,
EDNS and scatter boundary cases, with source assertions for one
kernel readv and preserved AEAD seal. Real Android TUN reception,
223.5.5.5 physical DNS socket runtime, 1.1.1.1 tunnel-specific
backend, DNS answer injection, Android Resolver interception and
per-App CN IP routing are still NOT_CONNECTED/NOT_RUN. Follow-up
B2c2b must qualify bound output/reply mapping **before** any packet
is diverted or dropped.
