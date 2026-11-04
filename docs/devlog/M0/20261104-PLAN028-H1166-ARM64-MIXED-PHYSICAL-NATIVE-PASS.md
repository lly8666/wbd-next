# PLAN028 H1166 — collect ARM64 mixed Game4 physical current-source PASS

Reaped [Action 41869940865](https://github.com/lly8666/wbd-next/actions/runs/41869940865), job126713948037, uploaded artifact13344212296, zipped SHA256 `6065797430b05cb87220f174c0080b27f1ec0dc93a8e8e8c9441632aad36b5a3`. Exact SOURCE `e5688364894ba0f60d71edb9547ed8e441b9e48a`, original mature Go `a7a82db3`, ARM64 ELF183 Go/Rust SHA in [evidence](../evidence/M0/PLAN028-H1166-SOURCEE568-ARM64-MIXED-GAME4-PHYSICAL-NORMAL-LIVE-PASS-20261104.json). Unlike prior H1162/H1164 failed fixtures, current native runner completed its own original Go TLS, Rust one-reader shared443, all UDP, per-client final Stop and OS-readback checks.

Three protected clients: Game2 off ChaCha, Game4 FEC fixed6 AES256, Normal Auto AES128; baseline 12+12+12 actual native UDP, Game2 isolated Stop then Game4+Normal +6 each. Game4 source IPv4 10.25.0.3→.9 and physical 1280 yielded new original TLS generation, exact old Stop, preserved Game4 /32 and inner OS 1358→1178, **32** new Game4 UDP. Independently healthy Normal Auto **48** replies straddled change/READY, OS inner 1375 unchanged and no Carol generation2. Shared Rust TUN exact final Stop PASS. Physical command→Ready **556.52ms** includes TLS/install, *not* notification 200/500ms budget. Precise notifier→TLS and auth→single first packet plus CPU/p99 remain NOT_MEASURED.

PLAN028 not complete. This specific new-path reauthentication does not fix/retroactively pass H998 original *same-connection* hot-shrink FAIL; old H998 ARM Game4FEC Action FAIL and remote ICMP/CPU causal NOT_MEASURED are retained. Next complete Linux task **x86_64/x86_64**, Windows excluded from rotation. No new Go/Rust/steady wire source, no duplicate matrix.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Append source-specific native ARM mixed physical session isolation PASS and correct outdated OPEN qualifier."}
```
