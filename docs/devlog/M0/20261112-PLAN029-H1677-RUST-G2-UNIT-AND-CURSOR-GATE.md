# PLAN029 H1677｜G2 Rust shared decision PASS + cursor limit repair

- Exact H1676 SOURCE `a5ef2cd0108946e380599895558b377f8686a208`, [G2 Action 43222375840](https://github.com/lly8666/wbd-next/actions/runs/43222375840) SUCCESS: original five-crate Rust compiled and **5/5** `plan029_split` pure tests PASS. These validate interval merging, route modes, own-purpose DNS egress, selective fake mapping rejection, domain exact/suffix and flow pin only—not real Windows D1–D5.
- H1676 governance Action43222375789 and maintenance Action43222375615 FAIL at `unbounded context_refs`: updated cursor had nine refs; schema max eight. Keep original files in repository, retire two redundant early evidence paths from **hot cursor references** while retaining later H1672 failure and H1675 source evidence; current H1676 Rust scoped SOURCE evidence added as sole evidence_refs.
- The old M0 PLAN012 combined-workflow Action43222375650 also failed before meaningful PASS (Rust toolchain download in job), not relevant to product D1–D5. No rerun of PLAN028/012 merely to mask this unrelated failure.
- Next: real no-WFP Windows 4-stage owned WAL/receipt and single Rust ingress to actual DNS/Direct sockets; prior real signed TCP kernel SYNACK failure preserved. No full PLAN029 PASS.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record five source-locked Rust pure split decision tests PASS_SCOPED; keep production Wintun and no-WFP Direct/DNS E2E NOT_QUALIFIED."}
```
