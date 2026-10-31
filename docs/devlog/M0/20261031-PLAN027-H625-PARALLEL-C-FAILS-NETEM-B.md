# PLAN027 H625 — collect parallel source593 and correct 106s native impairment control

Original Windows Go TLS+signed NPF/Wintun ↔ Linux Rust/raw TUN binary SOURCE `593ce4a1073773429d7739a086fe3e060af89a3d`, one product build [41195637726](https://github.com/lly8666/wbd-next/actions/runs/41195637726). H623 ten separate hosted Windows Actions returned **seven successes, three real failures** (see H625 evidence). FAIL 41197206789 is a Windows Rust worker `rc=3` before client Ready, so not capacity or 30% WAN-loss measurement. FAIL 41197211756 Fixed100 0% produced valid true bilateral UDP/TCP and owned Stop but Win first-delivery .997808 (below .999), Linux TUN tx_drop2171. FAIL 41197216400 Normal100/300s valid real duplex/Stop but Linux first-delivery .99086 and TUN tx_drop0. No C200 repeat or unsupported zero-loss banner. H624 separate Fixed105 idle/wake Action41197625979 SUCCESS.

H624 Normal/Fixed 106-second true underlay loss attempts 41197630321/41197633876 both **failed before injection** on `WL_B_BLACKHOLE_WRONG_SCENARIO`: new V2 parser admitted 106 but existing owned `tools/m0_wl_netem.py` still demanded 20. H625 one-line fix changes that guard to exact (20,106), no new kernel policy, no protocol/packet changes. Reuse the immutable source593 Windows and Linux binaries and launch **only these two unrealized B scenes** independently. New result is NOT_PASS until original full 106s blackout, genuine HealthDead/TLS reauth, UDP/TCP/Stop. Game FEC blocked, B rotation/DNS/IPv6/MTU still open. Source and failed artifacts retained.

```feature-impact
{"kind":"none","ids":[],"reason":"One original native test qdisc source-scenario guard fix, Actions source reuse, evidence/cursor only; no product code modified."}
```
