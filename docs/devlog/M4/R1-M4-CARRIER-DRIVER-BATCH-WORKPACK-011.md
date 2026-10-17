# M4 011 — carrier/driver/batch workpack (in progress)

Task: `R1-M4-CARRIER-DRIVER-BATCH-WORKPACK-011`, formally assigned by main registry revision 2 / epoch 1 / active branch `work/m4-r1-platform` in M0 PACK-006 (2026-10-17). Main at kickoff `103b8de8e5f1be6752cdfcf4753ee755e15fe804`; M4 clean prior H `e19772fe65d8cfb347da3c7b182c25180ba91d37`. No repetition of completed M4 001–010. Prior 010 scoped native 75/75 and historical failed runs remain exactly as recorded in its evidence.

## Scope and integration boundary

M4 owns `crates/wbd-platform/` and optionally `r1/go-bridge/`; M0 exclusively owns engine, root/Cargo/ABI, shared CI and product qualification. M0's already-main `linux_raw_carrier.rs`, `linux_route_events.rs`, `linux_tun_sink.rs`, and extended `linux_packet_preflight.rs` are integration baselines, **not** present on this older worker branch. No duplicate netlink listener, new TLS authority, or automatic AF_PACKET activation. Raw positive RX without CAP_NET_RAW remains RAW_RX_NOT_RUN; production Go V4 remains DISABLED.

## First implementation batch: typed native sendmmsg failure feedback

On the original platform `linux_batch.rs` add `KernelSendReport { outcome, signal }` and a nonallocating `submit_connected_udp_detailed` API. Existing outcome-only callers remain unchanged. A genuine negative Linux sendmmsg errno for EMSGSIZE/ENODEV/network loss means no accepted prefix and a typed invalidation; EAGAIN is backpressure, EINTR remains conservatively uncertain. Positive partial counts **lose errno**: confirmed prefix only, suffix unattempted, `PartialErrnoUnavailable` forces path refresh; no invented error code or peer ACK. STOP fences the call; frozen record bytes and PN/seq remain unchanged. This is an unprivileged UDP kernel syscall witness and classifier interface, **not** a real raw/TUN/DF MTU qualification.

New native tests: real kernel oversize UDP negative EMSGSIZE and first-good/second-oversize partial, plus deterministic typed device/route/interrupt/short-count branches. Old 75 cases are not reimplemented; existing tests run as a regression batch when Actions triggers on this code SOURCE.

## Remaining work inside this same authorized workpack

Bring M0's already-existing platform raw/TUN entrypoints into one integration-compatible M4 patch (do not overwrite M0 engine). Version and validate cached link/route MTU against the **single** M0 netlink revision source; refresh only on trusted change/error, DF/EMSGSIZE fail closed; raw/TUN ready-only <=32 I/O, reusable packet/iovec buffers, actual prefix/suffix/uncertain, stop/rotation and seq32 wrap tests. Explicitly distinguish CAP_NET_RAW absence and route/ifindex change privilege limits. After code/native Actions, preserve exact build/result artifacts and SHA evidence; S evidence then cursor-only H. M0 alone will wire original authenticated Go V4 owner and run end-to-end/performance/product checks.
