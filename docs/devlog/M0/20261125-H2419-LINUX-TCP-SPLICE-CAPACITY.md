# H2419 isolated native splice capacity diagnostic

User authorizes M0 to choose research order. H2418 actual zero loss proxy 298.316 Mbps vs NAT 267.212/302.689, 1% baseline varies ~10x. No evidence of severe splice bottleneck; no proof of multi-Gbps capacity. Keep production source unchanged. Compile exact production Rust module with rustc 1.85.1 opt-level3 and exact Go cold owner (only package name adapted); independent local kernel namespaces on one x86 VM, real TPROXY+NAT A/B/B/A, 0 added RTT/loss, 1500 MTU, CUBIC both endpoints, reverse single stream 20s omit2. Record actual receiver bytes, proxy copied bytes, process and host active CPU, raw logs. CPU includes warmup; compare as diagnostic not qualification. No WBD or 3 physical machines claim. If measured baseline or proxy capacity insufficient, diagnose owner and kernel first; no speculative product change.

```feature-impact
{"kind":"none","ids":[],"reason":"Only native capacity diagnostic harness and evidence; no production source or defaults changed."}
```
