# PLAN028 H1285 — rebase original FakeTCP queue invariant to the corrected handoff contract

At H1285 SOURCE `87f19510cf5ac8b934862a6c9187d47d0f796526`, ARM64 fast proof started, but full original `go test ./internal/faketcp` failed `TestStageTransitionBoundsCountAndWireSize`: the donor test encoded the *old defective behavior* that exceeding 64 staged pre-detach native records must ABORT the entire authenticated successor. This is an expected compatibility failure, NOT evidence that the replacement's new 64-record bounded-drop regression failed. Keep the old test and its 64-record/8-byte limits; revise only its verdict to `TransitionPrepared`, exactly 64*8 bytes, preserved queue and successful native Detach. Oversized single records remain `TransitionAborted` and the new H1285 malformed-source regression remains mandatory.

Exact donor test SHA `4a7ef97f3dd5971d9952114b39cf18c085aa29a7` to new overlaid result `a86374c83876519e4e5c785a8a3c8724f3f3d3e7`, captured in the original source-locked Go assembly manifest. Fast x86/ARM64 YAML additionally executes original FakeTCP ServerAssociation queued-overflow→Detach test before full package Go tests. This commit changes tests/assembly/fast validation only; no client/server binary behavior, cryptographic gate or protocol fields change. Latest source-specific real native 3×1800 status remains H1284 FAIL 1/3/10, H1285 not product-qualified.

```feature-impact
{"kind":"none","ids":[],"reason":"Original donor FakeTCP regression expectation now checks bounded early-data overflow preserves authenticated server Detach; tests, assembly and focused CI only, no additional product runtime change."}
```
