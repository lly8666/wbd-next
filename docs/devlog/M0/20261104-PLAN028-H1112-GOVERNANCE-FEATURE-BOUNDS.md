# PLAN028 H1112 — narrow governance metadata correction

H1109 original Go/Rust ARM64 product Action 41797983526 and H1107 x86 Action 41794271661 **remain actual native functional scoped PASS**. After H1110 evidence commit, governance Action 41798386966 reported two *metadata* faults: M0 cursor evidence_refs mixed distinct product SOURCES 32cd and 0e47; feature card exceeded the 16KiB catalogue bound. H1111 corrected both without modifying any product SOURCE, but Action 41798925070 feature catalog still rejected the feature-card edit because its commit had no accompanying devlog `feature-impact` block. Governance main structural job already passed.

This H1112 commit adds the required same-commit feature declaration and keeps card under 16KiB. Separate x86/ARM evidence remains in their individual files and feature verification entries; current ARM cursor evidence_refs only cite SOURCE32cd. No old tests rerun; H998 physical online shrink FAIL, historical ARM64 Game4FEC FAIL, remote ICMP, Win actual NIC/Npcap, Android, CPU/p99 and phase timestamps remain their truthful scopes. Next Windows native physical NIC/source IPv4 switching investigation, not a synthetic callback PASS.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1112 bounded metadata fix aligns PLAN028 x86/ARM scoped proof and preserves Windows/CPU gaps; no product code changed."}
```
