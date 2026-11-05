# PLAN028 H1248 — collect H1247 shared TUN A recovery, B continuous

H1247 exact source `3b40388c0a1c9fa6d6d19d3368e6e9f5aafd100a` targeted native Linux x86_64 Action [42064007729](https://github.com/lly8666/wbd-next/actions/runs/42064007729) / job127373027083 **SUCCESS**; artifact13432504318, SHA256 32924ec750266b7bb99ce462b604518478c19acc2fd9b5b826eea367077eaea9. Cargo Rust 1.85.1, 4/4 `m0_plan028_shared_tun_*` PASS in one built test binary.

Production enqueue+flush using bounded channel: A blocked two turns, first fills 8 packet pending, next 8 bounded overflow while B still receives. Then A drains exactly eight/turn for six turns, flush forwards eight each turn; 48 recovered A receives, 64 correct live B receives, **zero new A pending overflow** after recovery. No real network loss-rate or CPU p99 causal claim. The three older queue isolation/age/reclamation tests also pass. No protocol/MTU/FEC/crypto change.

First H1247 feature card append exceeded the `tools/feature_catalog.py` 16KiB per-card limit, causing Action42064007871 feature catalog FAIL although its governance job PASS. This H1248 documentation-only change succinctly merges the H1247 behavior into the existing feature limitation and shortens the summary, retaining old evidence/negative statuses. H1247 Rust/product source remains `3b40388c0a1c9fa6d6d19d3368e6e9f5aafd100a`; do not re-dispatch its targeted Action for this doc edit.

H1246 original Go+Rust Game2 physical native x86 Fixed6 and ARM Off previously SUCCESS at SOURCE830d5bc, but not silently rewritten into current H1247 evidence. Older PLAN027A H998 in-place MTU reduction FAIL, Windows full seven-mode physical, remote ICMP and Android/CPU gaps remain.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Compact source-specific H1247 shared TUN bounded-drain regression PASS into 16KiB feature-card limit; preserve historical scopes and PASS/FAIL."}
```
