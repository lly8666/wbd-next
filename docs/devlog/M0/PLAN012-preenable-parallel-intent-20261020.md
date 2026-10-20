# PLAN012 M0 parallel pre-enable Linux product qualification intent

Date 2026-10-20. Current registry: M0 `R0-M0-PLAN008-PRODUCT-VERTICAL-INTEGRATION-025`, revision2 epoch1, branch main. H200 recovery is CLEAN, HEAD `7398eeb18a00fda931b09dfbe0be29ad53c0c3a8`, open_requests=[].

## User mandate and refusal boundary

User asks to execute all prerequisite testing in parallel and directly enable Linux FEC2/Game **after** evidence. This is within M0 release responsibility, but cannot turn production on without **positive** original-Go public feature7 CLI Connect/Disconnect/cold APPLIED and independent Game2 and Game4 genuinely authenticated M4 raw kernel first-app. A native Game2/4 adapter or TLS-only cold collector is insufficient; one failed/missing gate is a stop, no workaround. All tests run on Actions; no Windows/physical/20Mbps pre-release requirement. Preserve production OFF before complete success.

## One bounded independent functional batch

Add source-locked `.github/workflows/m0-plan012-preenable-parallel.yml`:
- reuse existing original Go real Linux FEC+M2 Fixed/Auto + M4 Stop combined functional workflow once as same-SOURCE `baseline` job;
- three independent parallel jobs for exact original public Linux CLI product and separate Game2 and Game4 original Go → Rust M3 → M4 raw/TUN first-app tests. Each must execute a named non-skipped test in the actual pinned original Go module and must observe a case-specific explicit success marker. Missing test/source is `NOT_RUN`/preflight rejection, not PASS. No fake mock/native-only substitution or release toggle;
- fan-in `release-qualified` only if all actual jobs PASS. No Actions job may silently commit a production permission switch.

The existing `m0-plan012-combined-functional.yml` obtains `workflow_call` as an additional trigger with identical build/test semantics; new workflow itself is push-triggered exactly once by its new file. Avoid manually dispatching same request/run. Record all run IDs, attempts and failures and file/manifest identities. If prerequisites fail, retain production OFF and report exact missing evidence rather than spinning new seeds or repeating equivalent tests.

## Existing accepted, no rework

SOURCE `7dd10a2dcda165f408b9231d228345b328c9481a`, Actions39358619164, original TLS Game2/4 cold PASS scoped; prior M4 S46/FEC2 Fixed+Auto 2s rev4 APPLIED, native 2/4 Game are accepted scoped facts. Latest H200 Governance39359275342 SUCCESS. New parallel pipeline tests final release boundary, not a new task assignment or worker cursor.

## Next

After SOURCE-locked parallel gate outcomes, complete genuine missing product code on M0-owned integration paths and previously owned M4 product paths only with a single writer. Only after all positive can M0 commit Linux production ON with separate exact SOURCE verification. Incomplete delivery leaves cursor partial with one next action.
