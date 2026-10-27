# M0 H304 — recover S54 Auto true Applied, retain failed whole run, parallel safe scenarios

Authority: registry revision3, M0 assigned_task `R0-M0-PLAN008-PRODUCT-VERTICAL-INTEGRATION-025`, main sole integration writer, epoch1 unchanged, done_when remains product-scoped not green preflight. Read S55 branch as active experiment; don't move its in-flight artifact/source.

## Checkpoint and exact original Actions

Main H303 `7c30b7003f58bbdf48f664b09435cd0c15ed579c` was last green Governance and Feature catalog (Action40554247090). Main commit range audited: after H303 no implementation changes. Recovery independently inspected original S54 workflow40553530258/1 artifact12756438389 ZIP sha256 `706ed5294fd4dbb3f9e37f5babc082b9712f3c95cb97fc57d47fdbdaa572c82f`. Original signed Windows original Go TLS + Rust M1/M2/M3 + native Npcap/Wintun/WAL ↔ Linux raw/TUN ready PASS; actual kernel UDP both directions 79320/39668 source packets and TCP both ways PASS. Windows Rust M2 native Applied of rev2/profile4, rev3/profile3, rev4/profile2 before native 1Hz sample38 showed at least **one real grade lowered within the user 120s limit**. However original full Action **FAIL**, because Python test expected `auto_revision_pending` JSON key to be present with false; original Go uses `omitempty` and omits false. So the full native owned Stop did **not** finish: `NOT_RUN`, not FUNCTIONAL_PASS. Exact evidence `docs/evidence/M0/PLAN025-S54-Auto-natural-source0af9b585-applied-fixture-failure-20261028.json`. The S52 actual no-downshift FAIL is untouched, as are S45 Auto and S51 preflight red.

S55 `49f816375a9e69bd1cde41df2543b15b58066313` only repairs test interpretation: missing pending key counts as false **only** when positive Rust-backed applied==requested revision, strict profile<5 and no policy error. Action40556191100/1 was RUNNING at this checkpoint; Windows Go and Rust/Go Linux preflights PASS, Windows native verdict pending. Its Feature catalog governance Action40556191268 **FAIL** since S55 existing `fec-auto` card exceeds 16KiB limit; resolve catalog separately with concise pointers rather than weakening checker or discarding source facts.

## Independent experiments, no race with Auto owner

User authorized running relevant distinct scenarios concurrently. Measurement-only branch `experiment/windows-wiring-n0-normal-parallel-20261028` copies immutable S55 product source; initial Action40556823589 preflight **FAIL** due workflow global manual N0 env change, preserved. Corrected exact source `aa93183d7183681efd5408f3cb2e1a0d1e32fada`, Action40557095692 in progress, preflight PASS. Its single scenario is Normal/off WL-N0 10Mbps, real Linux kernel IFB/tc 0%-loss 300ms each direction on own Windows hosted VM with offered/delivery/Stop/CPU readback. A failed N0 cannot be relabeled environmental without direct/host evidence; do not add N1/N5 pressure if capacity insufficient.

ARM64 independent branch `experiment/windows-wiring-arm64-native-parallel-20261028` exact `f7ee097e116ab813f9ba23514df01a3f0f9d342a` Action40557336142 running; native ARM64 Go/Rust original-TLS bundle, reusable hash-locked binary and separate real TUN/netns bidirectional functional+Stop. It is neither Windows functional nor ARM64 scored performance. Both experiments have only test trigger/intent changed, no production code, do not introduce new task or epoch and do not merge branch-specific workflow overrides into main.

Remaining needed: S55 true full Auto positive incl owned Stop; actual loss-driven rapid Auto rise (transition packet loss allowed); independent N0/N1/N5 and old/new sequential CPU/p99; full GUI/global WFP/DNS, physical, MTU boundary specific qualifiers remain NOT_RUN as before. No further stress before runner capacity readback. Keep all failures and separate SOURCE/platform qualification.

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Record first genuine source-locked Windows Rust M2 natural downgrade inside 120s while preserving overall S54 failing fixture and NOT_RUN Stop, track S55 and independent network/native qualification without product promotion."}
```
