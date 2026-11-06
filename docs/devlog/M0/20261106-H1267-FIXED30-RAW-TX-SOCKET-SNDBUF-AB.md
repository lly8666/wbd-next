# PLAN028 H1267 — identify original Normal Fixed6 M4 EAGAIN with cold socket resource A/B

## Prior SOURCE-locked defect boundary

The original authenticated Go TLS/Rust M0 H1263 180s three-client raw/TUN Action42145967317 SOURCE `8ddab1219132f6206c53fca501fc972fcb5ca11b` proves low-frequency same-PN/SEQ Game2 OFF cosmetic sends **1082 per side** under 5% actual qdisc loss; no PN, AEAD, FEC, business or authenticated-ACK credit. That repair is complete. Separately, 30%-loss NormalFixed6+125ms one-way client original M4 `sendmmsg` encountered a **typed EAGAIN backpressure** streak (+3938 event reports, zero copied packets over 2.5023s, despite +6317 authenticated FEC2 sources accepted); the remote real original raw+FEC2 RX remained empty 3.023s while application uplink kept sending 16Mbps. Original source ZIP archive and H1265 offline posthoc Action42149220835 verified the M4 stage and no server shared TUN queue overflow. The earlier H1259 430s opposite **S2C** Fixed6 late blackout is not assumed to share the same cause.

## Why not change FEC/retransmit yet

Native M4 `ScopedRawIpv4Tx::send_kernel_multimsg` executes one bounded original 32-packet nonblocking Linux `sendmmsg(MSG_DONTWAIT)` on an exact per-socket `IPPROTO_RAW` FD. A known zero-prefix `EAGAIN` is typed `KernelSendSignal::Backpressure`, with **no fresh PN, no reseal, no old-cipher retry, and no delivery credit**. The available evidence does not yet tell whether the raw socket is writable, effective SO_SNDBUF is small/capped, the per-egress qdisc/driver is congested, or the M4 worker is scheduling poorly. Do not hide the issue with unlimited PN reuse, higher FEC2 parity, altered FEC2 aging, or cosmetic retries.

H1267 adds only read-only Linux kernel socket telemetry and a **cold, experimental developer-only** `SO_SNDBUF` request:
- Default original raw M4 socket unchanged, requested-byte diagnostic `0`.
- Experimental `WBD_M0_RAW_TX_SOCKET_DIAG=1 WBD_M0_RAW_TX_SNDBUF_AB=1048576`: immediately after the new authenticated Linux RAW TX socket opens and **before** ownership publication, request exactly **1MiB** via SO_SNDBUF, never SO_SNDBUFFORCE. Linux may cap to `wmem_max`; accept only and record **actual kernel effective getSOCKOPT bytes** (limit2MiB). Invalid values fail closed; no global sysctl/qdisc/MTU/FEC/Go code changes.
- Report original per-session socket effective SO_SNDBUF and `poll(POLLOUT,0)` + optional read-only `SIOCOUTQ` at socket open and only every **64th typed EAGAIN**, max128 probes per TX owner (default if env disabled: zero extra hot-path syscalls). Final Stop reports EAGAIN totals, writable/not writable samples, actual OUTQ high water and errors. POLLOUT is a momentary readiness sample, **not** proof of kernel acceptance.
- Add socket ABI regression on an unprivileged ephemeral UDP FD to verify typed invalid requests cannot modify the buffer, requested1MiB obeys kernel clamping and actual SO_SNDBUF readback matches. Raw socket privilege/capability and immutable M4 handle ownership unchanged.

## Actual source-locked short A/B

One GitHub Actions x86_64 native VM, **two sequential 120s legs** (no simultaneous duplicated packet owners): default original RAW TX socket then requested1MiB; each leg includes two independently authenticated original Go TLS clients, A NormalOff/0%/12Mbps and E Normal Fixed6/30%/125ms one-way/outer1280/16Mbps, one original protected Go TLS server443 and Rust TUN; physical native tc netem `limit10000` on both directions; actual rate/packet unique UDP (no app retries), 10s warmup,30s steady,35s 1.3× overload,45s return-rate recovery,10s drain. Same SOURCE/Go/Rust/ISA-L binary SHA and kernel namespace host, distinct scoped bridge/veth/leased auth identities per leg. Original 500ms FEC2 M4 counters allow identifying longest contiguous EAGAIN/zero kernel copy span under new accepted FEC2 sources; separately record true receiver throughput, underlay loss and per-authenticated-lease server TUN overflow.

If requested1MiB is completely clamped to the same effective buffer, **DO NOT claim a capacity A/B**. If no EAGAIN streak appears, diagnosis remains inconclusive for the intermittent H1263 failure; do not promote unconditional socket knob to public defaults. If an actual larger buffer measurably reduces streaks and improves recovery under matched load, only then consider a separate narrow default product change with source-scoped revalidation. Original H1263 cosmetic functionality PASS, H1259 fixed30 historical late S2C deficit and H998 same-socket online MTU shrink FAIL remain separate.

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"Cold, developer-opt-in Linux original RAW TX effective SO_SNDBUF/POLLOUT/OUTQ diagnostics and constrained source-locked test only; no production M4 delivery, retry, PN, FEC or protocol change."}
```
