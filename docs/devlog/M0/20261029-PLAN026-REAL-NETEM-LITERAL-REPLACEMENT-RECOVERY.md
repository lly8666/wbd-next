# M0 PLAN026 H356B — recover whole-script after literal replacement

2026-10-29. Follow-up independently pinned V4 Wiring Action 40838486087 failed **Fixed and Auto only** with `trace-netns.sh: line 311: syntax error near unexpected token '('`; Game2 and Game4 checks passed. The application log already had 64 genuine FEC echoes; this was fixture shell syntax, not a FEC/PN/Go TLS regression. Inspected the main script: the previous JavaScript string replacement interpreted `$'` inside the strict regex as a replacement-control sequence, splicing the old script suffix into the new branch and duplicating/truncating subsequent shell. No source protocol implementation was altered.

Minimal restore in `84292ac25b552208f1d9a22c90e76f338b19b405`: rebase **the entire script file** on verified pre-edit SOURCE `0caf60bb`, apply the same first-unique loss selection with a literal replacement callback and strictly check whole-script line count, final branch and exact quote before writing. The source now has 350 lines, complete unchanged real tc/M2/Stop Python receipt proof and intact Normal/FEC/Game cases. The intended 1pct behavior is unchanged: offered512, delivered/missing real, no outer recovery contract. New exact SOURCE combined and separate Wiring Actions must decide, not this static inspection.

H356 cursor 91a0378b restored `last_tested_source=b9c2c170` to match older signed 50/100Mbps evidence; governance 40838524102 completed both Governance and Feature catalog SUCCESS. Earlier failed SOURCE runs remain failed, never overwritten. Not yet qualified: 1pct new SOURCE, Windows full NativeOwner functional/cost A/B, V2 complete mode matrix, physical.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct literal replacement corruption in test-only Actions shell fixture while restoring exact pre-edit content and preserving true UDP source accounting; no product code/feature changed."}
```
