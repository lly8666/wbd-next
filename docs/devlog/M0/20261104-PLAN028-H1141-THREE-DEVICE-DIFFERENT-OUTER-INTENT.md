# PLAN028 H1141 — genuine independent three-client user outer MTU, frozen x86 product

Latest whole native Linux task H1139 ARM64/ARM64 SUCCESS, so this next distinct Linux task is x86_64 client + x86_64 server. Reuse exactly the H1135 original Go TLS/Rust SOURCEab472 x86 ELF62 binaries (Action41822046885 artifact13317049005), validate all SHA256 in original manifest; no QEMU, no mixed ISA, no product rebuild.

The existing mature 4-original-TLS-session native netns fixture tests Bob plus Alice two separate installations and one same-installation A→A+B→B; old historical tests only varied the *physical path* MTU for Alice, not independent per-device *user requested complete outer IPv4 IP MTU*. This one narrowly changed source-frozen ephemeral copy applies `--outer-mtu 1280` ONLY to Alice's second installation D, while A/R and Bob remain default1460. Demand authentic original client SYN advertised MSS 1420/1420/1240, actual kernel inner client TUN 1389/1389/1209, and unchanged shared server TUN1389 (never lowered to 1209), not computed-only. Then original real application UDP 70 total across A/B/D/replacement, sibling Bob and Alice-D continue around A reauth, old exact-generation and all per-client Rust/TUN Stop join, no copy to all clients. One server443, original account authentication+installation lease and distinct /32.

No new schema, helper-specific native dispatch, per-packet FFI, second owner or additional test matrix. Explicitly NOT a proof that client D may also choose Game4/FEC6 while others Normal: mixed modes are a separate actual integration gap, under source inspection. Hardware Wi-Fi/cellular/Android NOT_RUN; H998 old same-connection MTU hot shrink FAIL; CPU causal old/new NOT_PROVEN.

```feature-impact
{"kind":"none","ids":[],"reason":"One separate original source-frozen Linux x86/x86 multi-client outer user MTU readback and 70-UDP business scenario; no product source or feature behavior changed."}
```
