# PLAN028 H1152 — repair one extracted original Go Normal owner scope before native mixed business

[H1151 Action41846579568](https://github.com/lly8666/wbd-next/actions/runs/41846579568) stopped at original Go compile with `bridge_v4_linux_server_product.go:230:12 undefined: err` (and follow-on same variable references); new Normal+Game mixed native scene never started. The original singleton `AcceptAuthenticatedPeer` used to declare `err` before the native post-TLS branch; the shared `startAuthenticatedNormalLocked` helper extracted those assignments but did not carry the local declaration. This is not a packet/wire failure or old regression.

H1152 fixes the **one declaration only** (`var err error`) in the existing shared Normal original Rust post-TLS method and adds `TestPLAN028MixedOne443OriginalProtectedNormalGame2Game4ColdPolicy` to the same H1151 workflow, covering source-locked original Go TLS cold policy for Normal off/fixed/auto and Game2/Game4, plus feature7 negative. Same one genuine x86_64 client+server scene will then check concurrently A Game2, B Game4FEC6, C NormalAuto over one443, 48 actual UDP, A-only Stop and B/C survival, full native Rust/TUN Stop. One build per SOURCE, no duplicate historic matrix or new protocol.

Preserve H1149 ARM/ARM current fixed6+ciphers success, H998 old same-connection hot shrink FAIL, old ARM Game4 Action FAIL, remote ICMP, Android/physical Wi-Fi and CPU causality NOT_PROVEN. H1152 is NOT yet native PASS.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Exact original Go compile fix for new mixed-mode native owner method, plus new protected mixed-mode original TLS test in source-frozen x86 workflow; no functional PASS claimed."}
```
