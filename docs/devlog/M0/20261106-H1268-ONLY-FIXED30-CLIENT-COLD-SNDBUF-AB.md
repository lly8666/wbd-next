# PLAN028 H1268 — same-VM Fixed6 client-only raw M4 socket A/B after H1267 mixed-direction result

H1267 exact SOURCE `dae5d7f5bba6120fd297458face00415bc0d9b49`, native Actions [42152888809](https://github.com/lly8666/wbd-next/actions/runs/42152888809) SUCCESS, artifact13473901999 original ZIP SHA256 `fcdd88b043b29f29138238340b9615a4ac723b7ad40569dbe05c2f4115d412bb`, 57 entries CRC PASS. Two 120s real original Go TLS/Rust x86_64 sequential same-VM legs, A NormalOff0% and E NormalFixed6 30% loss/125ms each way, tc netem limit10000 with true physical30% both directions; 10s warmup,30s steady,35s 1.3x overload,45s return normal and10s drain. Client/server binaries byte-identical between legs; original raw M4 frozen/no reseal/no PN reuse, FEC6 and outer unchanged.

| Metric | all raw sockets default | cold request1MiB on ALL sockets |
|---|---:|---:|
| actual Linux SO_SNDBUF effective | 212,992 | 2,097,152 |
| Fixed30 client typed M4 EAGAIN | **4521** | **0** |
| 1/64 EAGAIN POLLOUT samples | 70/70 **writable**, outq0 | 0 samples |
| longest TX accepted-source but no M4 successful prefix | 1.5022s | no observed span |
| Fixed30 overloaded uplink UDP unique delivery | **93.8221%** | **99.9843%** |
| Fixed30 recovery downlink UDP unique delivery | **99.9912%** | **92.6635%** |

**Interpretation:** A real enlarged kernel raw TX send buffer plausibly fixes the original local client M4 blocked-send phase, since EAGAIN suppressed and 30% physical loss plus actual app send were matched. But H1267 altered **both server and client** raw TX send buffers; 92.66% recovery downlink in that leg is a real business residual, not an all-mode perf PASS. POLLOUT remained writable on all 70 diagnostic snapshots after EAGAIN and SIOCOUTQ read zero; these samples are not reliable proof of specific kernel allocation exhaustion or guaranteed admission. One sequential one-VM A/B is not strict CPU causal identification.

H1268 changes **only** test fixture and reporter; the tested original Rust/Go release implementation remains exactly H1267. Run default→client-only 120s/leg same-VM original TLS+Rust with the same modes/rates/netem. For tuned leg only E's process receives `WBD_M0_RAW_TX_SNDBUF_AB=1048576`; server and A explicitly receive `default` in **both** legs. Oracle requires effective readback on *all* sockets before comparing, exact two authenticated leases, two-way native app unique delivery, true ~30% tc loss and 500ms original M4 source+kernel+EAGAIN counters. No app retries, new AEAD PN, FEC parity/cache/MTU changes, global sysctl, normal/Game cosmetic traffic adjustment, or repeated 430s long matrix. If client-only leg has stable recovery and zero EAGAIN, consider a **separately source-qualified** bounded cold product default for owner Fixed6 clients; do not grant release status from the diagnostic alone.

Archived original H1263 Game2 OFF same frozen outer copies1082 each direction remains functional PASS. The previous H1259 Fixed6 S2C blackout and H998 same-socket hot MTU failure remain historical until separately proven.

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"Archive exact H1267 native SO_SNDBUF diagnostic with adverse downlink result; H1268 restricts test request to Fixed6 client only. Product code, wire, PN/FEC/outer and default socket behavior unchanged."}
```
