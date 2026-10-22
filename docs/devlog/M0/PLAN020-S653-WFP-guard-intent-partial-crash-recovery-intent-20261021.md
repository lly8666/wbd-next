# M0 PLAN020 S653 — exact guard-intent partial crash recovery intent (2026-10-21)

## New correctness finding and authorized boundary
The already-source-locked `N4NativeUnifiedTxn.Recover` rejects a guard-only WAL `intent` where actual WFP state is `N4UnifiedPartial`, although `n4WFPArmExactPlan` is a crash-persistent multi-object operation and original `n4WindowsGuardStage.Undo` has the exact-owned `DisarmAfterRoutesRemoved` partial cleanup. The stored WAL pre-dates the mutation; without cleanup this strands persistent host policy. This is within PLAN020 WFP crash recovery, not a new package.

Smallest safe fix: permit `guard` as sole last intent record at `i==0` when independently observed `Owned` OR `Partial`; continue refusing foreign, all later non-guard intent partials, and any partial guard while later lease/DNS/routes records remain. Reverse WAL CAS should call only exact-owned WFP `Undo`; no broad host reset and no fake return. Add pure native unit positives/foreign and retain existing guard-before-routes negatives.

Pre-existing S652 source `b3a8fbaf23419a300d7eb5d17ce315d754ae1cb5` native TEST-NET WFP Arm Action `39616586763/1` was **queued** when read; its eventual result must be recorded distinctly, never inferred for this future SOURCE. One new exact-source Windows native functional Action will be triggered by relevant path changes; do not redispatch S652. All host-global WFP, default /1, full original public OS+GUI, physical, perf remain NOT_RUN and OFF.
