# PLAN028 H1136 — correct source-specific active evidence index

H1135 real native Windows/WSL2 original product Action41822046885 is already in flight. The prior M0 governance gate correctly rejects a cursor that lists different compiled SOURCES under one active `last_tested_source`: H1130 ARM SOURCE32cd and H1133/H1134 Windows SOURCE1bb were mixed. This metadata checkpoint keeps active Windows source1bb evidence_refs only, and adds the standard exact `source_sha=1bb739` to H1134 original evidence. H1130 ARM evidence stays in the original immutable file and devlog. Nothing from the original Go/Rust binary, shared session, native test or feature catalog changed, and no additional Windows Action is dispatched.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix active-source evidence metadata only, no source feature or runtime behavior changes."}
```
