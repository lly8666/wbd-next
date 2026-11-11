# PLAN028 H1578 | repair offline stale Stop expectation before first 1.15x native pilot

[H1577 Action42983313447](https://github.com/lly8666/wbd-next/actions/runs/42983313447) SOURCE `d3d9955e58c8a551c893e16522c267e2022071c9` failed **PRE_NETWORK**: 18 of 19 offline source guards passed, one old H1572 test still searched the non-existent `V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server` text removed by H1576's already-reviewed true Rust canonical server Stop. **Zero Windows2025 native product network test occurred**, so the 1.15x calibrated load is NOT_RUN. Original Action FAIL remains in evidence; do not call it product FAIL. The new H1577 source assertions for actual all-six app rate control and the 150s fail-closed capacity/UDP/TCP/owned Stop gates passed. H1576 600s offline guard carried the same stale literal and now participates in the cheap preflight too, to catch errors before native build.

H1578 changes **only** the two stale test strings to real original Rust `V4_PUBLIC_SHARED_TUN_STOP generation=` and includes H1576 600s source contract in cheap checks; source-tested product Go/Rust, original 1460 MTU, reliability behavior, native rate, all true owner hard gates unchanged. The commit uses the same single original H1577 1.15x Action marker because **its network was never dispatched successfully** on H1577. Original 150s 24Mbps/dir real five-client PASS_SCOPED remains reused, no replay of it or 30% long test.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct stale offline test-only original server Stop marker, enabling first real Win1/Linux4 1.15x L2 source-locked trial with existing product and strict native gates unchanged."}
```

Evidence [H1577](../evidence/M0/PLAN028-H1577-WIN5-L2-115PCT-NATIVE-20261111.json), [H1578](../evidence/M0/PLAN028-H1578-CAPACITY-PREFLIGHT-REPAIR-20261111.json). PLAN028 IN_PROGRESS.
