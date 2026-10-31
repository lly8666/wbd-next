# PLAN027 H674 — recovery cursor source/index schema correction

H673 push [Governance run 41236461879](https://github.com/lly8666/wbd-next/actions/runs/41236461879) failed *only after* genuinely recorded H669/H671: scope audit `unbounded evidence_refs` (9 > 8), also its mixed dc191 and source6ece historical refs cannot satisfy current SOURCE evidence equality. Preserve original H657–H665 source-dc191 evidence unchanged and all H673 source-cross-check facts. Here cursor `evidence_refs` contains only exact original SOURCE6ece H672 and H673, with explicit `source_sha` on recovered H673 evidence; historical docs remain linked from H673 devlog and PLAN027 index. The 5M real scenario run 41236475558 uses built SHA6ece and is in flight, never turn governance recovery into product PASS or re-dispatch. Current task remains PARTIAL.

```feature-impact
{"kind":"none","ids":[],"reason":"Governance/schema-only cursor source-provenance and recovered evidence metadata; no product code, effective configuration, or test scenario modification."}
```
