# PLAN028 H1177 — native ARM64 physical-down direct TLS recovery PASS

Collected [ARM Action41885126982](https://github.com/lly8666/wbd-next/actions/runs/41885126982), native AARCH64 client+server, current SOURCE `baa1e9b9e1efe287108c5c151fce09d76f8ab29c`, original Go TLS / Rust M4 artifact13350418540 zip SHA256 c382accb781ee6724b2b82752092c4cf060c91892cb6e188242ea92f88261d2f. Actual netns mxb0 physical link DOWN **1331.81ms**, OS interface revived with source4 10.25.0.9 and 1280 IP MTU, old generation1 TERMINATED before original Go TLS/M4 generation2 new READY (old_generation=false). Physical command→Ready **1619.91ms** includes outage and handshake; not 200/500ms notification coalescing SLA. Same protected account/TUN lease preserved, configured outer1460, Game4 inner OS1178, other Normal Auto1375 unaffected. True Game4FEC6 new UDP32, healthy Normal Auto real48, original shared server TUN final Stop PASS. No false old owner overlap; no Android/ICMP/CPU/p99 claim. [Evidence](../evidence/M0/PLAN028-H1177-SOURCEBAA1-ARM64-GAME4-DOWN-FIRST-REAL-AUTH-PASS-20261105.json).

Next full Linux platform **x86_64+x86_64**, seek genuine 5% random-loss stage during Game4 physical replacement and real p99 (do not reopen old 027/027A loss matrix). Windows H1175 [signed Game4 action41884844001](https://github.com/lly8666/wbd-next/actions/runs/41884844001) separately in-flight, no duplicate. H998 original same-connection MTU shrink FAIL, old ARM Game4 Action FAIL, remote ICMP unmeasured and CPU causal unproven retained.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Record current-source original TLS/Rust native ARM64 link-down direct recovery qualified PASS with existing historical failures."}
```
