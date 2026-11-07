# PLAN028 H1298 — per-client native RAW TX confirmed EAGAIN

H1297 native ARM64 real five-client 180s original TLS443+Rust M4 [Action 42332967232](https://github.com/lly8666/wbd-next/actions/runs/42332967232) FAIL one Erin **downlink** 2160ms t+8.97–11.13. Genuine independent CLOCK_MONOTONIC stage traces prove server exact client_port45031 M4 kernel copied stalls while native TX Backpressure rises 1047, client Erin raw observed/tuple/FEC/TUN stops ~1.5s, other 4 still pass. The server application sent 1,973,248 bytes during the 2.16s gap; authenticated rotations all 5 PASS and server /32 shared TUN overflow0. Not client FEC decoder or shared TUN queue.

H1267 original RAW TX both-sided requested1MiB SO_SNDBUF (kernel effective212992→2097152) eliminated actual EAGAIN4521 in one same-source A/B but another real downlink interval still failed. It does NOT justify blanket defaults. H1298 handles exactly the observed per-socket scarce capacity: after **eight consecutive** native `KernelSendSignal::Backpressure` on an authenticated FEC2 M4 worker, use its existing bounded Linux SO_SNDBUF setter **once** (requested1MiB, readback kernel effective<=2MiB) for that owner only. No global sysctl, extra packet thread, TLS/Stop wait, old ciphertext resend, PN reseal, packet format/FEC/policy changes, or unqualified success assertion. This consumes <=2MiB native socket memory only on a troubled owner, unlike unconditional five-client enlargement.

An unprivileged native Linux UDP socket tests exact setter/readback and once semantics; same SOURCE original ARM64 ISA-L five-client pressure180s verifies true app, Stop/rotation and may observe adaptation marker. One Action, one scene. If EAGAIN does not occur or gap persists, no causal improvement claim. Old H1295 native/scalar/hetero failures, H998 remote ICMP and old-socket MTU FAIL retained. No 1800s.

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"Bounded one-time native Linux RAW TX SO_SNDBUF only after eight genuine consecutive FEC2 M4 EAGAIN turns, no unconditional default or wire/FEC/PN changes."}
```
