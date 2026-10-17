# M4 011 — carrier/driver/batch workpack (in progress)

Task: `R1-M4-CARRIER-DRIVER-BATCH-WORKPACK-011`, formally assigned by main registry revision 2 / epoch 1 / active branch `work/m4-r1-platform` in M0 PACK-006 (2026-10-17). Main at kickoff `103b8de8e5f1be6752cdfcf4753ee755e15fe804`; M4 clean prior H `e19772fe65d8cfb347da3c7b182c25180ba91d37`. No repetition of completed M4 001–010. Prior 010 scoped native 75/75 and historical failed runs remain exactly as recorded in its evidence.

## Scope and integration boundary

M4 owns `crates/wbd-platform/` and optionally `r1/go-bridge/`; M0 exclusively owns engine, root/Cargo/ABI, shared CI and product qualification. M0's already-main `linux_raw_carrier.rs`, `linux_route_events.rs`, `linux_tun_sink.rs`, and extended `linux_packet_preflight.rs` are integration baselines, **not** present on this older worker branch. No duplicate netlink listener, new TLS authority, or automatic AF_PACKET activation. Raw positive RX without CAP_NET_RAW remains RAW_RX_NOT_RUN; production Go V4 remains DISABLED.

## First implementation batch: typed native sendmmsg failure feedback

On the original platform `linux_batch.rs` add `KernelSendReport { outcome, signal }` and a nonallocating `submit_connected_udp_detailed` API. Existing outcome-only callers remain unchanged. A genuine negative Linux sendmmsg errno for EMSGSIZE/ENODEV/network loss means no accepted prefix and a typed invalidation; EAGAIN is backpressure, EINTR remains conservatively uncertain. Positive partial counts **lose errno**: confirmed prefix only, suffix unattempted, `PartialErrnoUnavailable` forces path refresh; no invented error code or peer ACK. STOP fences the call; frozen record bytes and PN/seq remain unchanged. This is an unprivileged UDP kernel syscall witness and classifier interface, **not** a real raw/TUN/DF MTU qualification.

New native tests: real kernel oversize UDP negative EMSGSIZE and first-good/second-oversize partial, plus deterministic typed device/route/interrupt/short-count branches. Old 75 cases are not reimplemented; existing tests run as a regression batch when Actions triggers on this code SOURCE.

## Remaining work inside this same authorized workpack

Bring M0's already-existing platform raw/TUN entrypoints into one integration-compatible M4 patch (do not overwrite M0 engine). Version and validate cached link/route MTU against the **single** M0 netlink revision source; refresh only on trusted change/error, DF/EMSGSIZE fail closed; raw/TUN ready-only <=32 I/O, reusable packet/iovec buffers, actual prefix/suffix/uncertain, stop/rotation and seq32 wrap tests. Explicitly distinguish CAP_NET_RAW absence and route/ifindex change privilege limits. After code/native Actions, preserve exact build/result artifacts and SHA evidence; S evidence then cursor-only H. M0 alone will wire original authenticated Go V4 owner and run end-to-end/performance/product checks.

## Integration-compatible owned Linux baseline (source-scoped staging)

Frozen M0 baseline main exact SHA `e9be1e716070256bbd4b351dd85452d8f2553266` imported platform-only `linux_packet_preflight.rs`, `linux_raw_carrier.rs`, `linux_tun_sink.rs`, and `linux_route_events.rs` unchanged to this worker's authorized `crates/wbd-platform/`, with only the necessary platform `lib.rs` cfg module registration. This is not an independent new netlink watcher or Go/engine bridge. No main/root/Cargo/ABI/CI or physical interface was modified. The fixed baseline still invokes per-send kernel MTU observation, so follow-up M4 work is to version a cached MTU against that single route/link watcher, keep fail-closed before send on revision change, and prove STOP/DF/EMSGSIZE boundaries with native tests. Until exact Actions on this SOURCE, this staging commit is **UNVERIFIED**; do not attribute M0 old green to this worker SOURCE. Existing actual raw positive/TUN privileged native remains NOT_RUN; production GoV4 features0.

## M4 owner-cache MTU follow-up (source pending native)

The original pinned M0 raw TX/RX per-DATA `observe_interface_mtu` calls were replaced in the M4 branch only with `ScopedRouteBudget`. It uses the imported **single** `linux_route_events::subscribe()` revision source, cached link/route PMTU bounded to the original link MTU and validated ifindex/generation, a 100ms revision debounce (changed rev cannot use old budget), at-most-1s TTL recheck, and a permanently invalid owner state on a real kernel EMSGSIZE/ENODEV/route-down/short send. The Linux kernel still checks actual DF/PMTU on each send. If watcher is unhealthy or route cannot be authoritatively refreshed, fail closed rather than doing an untrusted per-packet UDP fallback. The RX fast path likewise reads no sysfs. Real raw send remains gated by CAP_NET_RAW, so only pure/native negative/cache tests are source-qualified by the next Actions; no raw positive or performance proof is inferred.

## Bounded raw ready-only interface (native tests required)

`ScopedRawIpv4Tx::send_ready_batch` handles 0/1/32/33 frozen records with a known accepted-prefix/unknown-one/unsent-tail ledger; it deliberately consists of at-most32 synchronous `sendto` calls instead of falsely calling this multishot sendmmsg. Real kernel EMSGSIZE/ENODEV fail closed against the owner-local revision cache, STOP registration uses the original BorrowFence. `ScopedRawIpv4Rx::receive_ready_batch` polls with zero timeout and bounded <=32 independent caller buffers, MSG_TRUNC identifies original wire length and strict IPv4/TCP parser produces only unauthenticated ciphertext + seq32, never PN/Go authority. These are compile/pure-tested only unless a privileged isolated raw runner actually observes packets; do not claim real raw-positive or performance. TUN remains a distinct device type, not a raw packet FD.
