# H2438 scoped acceptance and integration review

H2438 acceptance and integration review: docs/evidence/M0/20261125-H2437-SELECTED-FIXES-ACCEPTANCE.json, docs/decisions/M0-TCP-SPLICE-INTEGRATION-H2438.md. H2437 both Actions successful, 24/24 Linux EOF/count/Stop both Normal1024, 4/4 finite 4GiB SHA256, original Go oracle +156 Rust codec passes, Windows8MiB scoped signed driver/kernel TCP WSL2 PASS, full product NOT_RUN. All10 paced legs local queue drops0; ARM0 ~510 vs540–546 with lower wire, ARM2% ~401–405 vs314–322 with higher wire within600. Keep pacing ability; no unconditional fixed per-flow cap. Current proxy native splice already integrated at kernel TUN boundary; control-plane integration valuable, no L4 record redesign, no speculative hot path rewrites. Shared-TUN scratch/Vec/M1 copy candidate deferred absent evidence. Production NAT/fq600 unchanged, uncapped test differs; release gate product config, multi-flow/Auto FEC, full Windows/remote/old kernel. End base performance optimization, no new run or product source change.

```feature-impact
{"kind":"updated","ids":["linux-tcp-splice-proxy"],"reason":"Record H2437 scoped acceptance and source-based integration decision; no product promotion."}
```
