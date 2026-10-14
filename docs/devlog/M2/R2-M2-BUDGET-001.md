# R2-M2-BUDGET-001 · independent fake-clock F/R/L accounting atom

Owner M2, active rev2/epoch1. Prerequisite reviewed worker/main sync SOURCE cfc77b9 fully verified 14/14; evidence S9e786cf; cursor-only H7603776 Governance38560192366 SUCCESS.

**Implement:** per-tunnel *direction* pure RepairBudget as a shared accounting owner for all lanes in that direction, not a per-lane quota. 1s monotonic epoch, F only confirmed fresh outer-wire IP+TCP+record data bytes (includes initial FEC/Game, excludes control/unknown initial sends); R includes reserve-before-dispatch repair bytes and Accepted/Uncertain. Gate max(F/10,32768) in integer bytes, never sum percentage + floor; additionally configured absolute per-epoch ceiling. Sparse traffic uses 32KiB absolute floor, not a 10% share. Separate 8*outerMTU capped token-pacer spanning epoch, last-epoch recent rate for pacing only, no carry-over of unused epoch quota. Fresh accounting has no dependency on repair quota.

**Bounded result ownership:** max pending reservations and bytes, <=1s bounded send-result deadline, unique checked reservation ID; definite NotSent refunds *its original epoch*, Uncertain and timeout retain debit and cannot become a second free retry. Duplicate/late send completion returns Stale and never double accounts; timeout residual tracked as conservative debt, finite metadata. No socket, clocks read, PN creation, seal, engine, platform or Cargo edits. FrozenRecord repair candidates originate from M2 receipt and remain the original ciphertext handle/PN. ReceiptState itself retains its existing <=2 accepted/uncertain retry cap and 20ms queue/expiry preflight. Engine must still call ReceiptState::preflight before syscall and attach per-frame actual carrier wire byte count.

**New compiled native r2_ fake-clock fixtures:** sparse floor quota, high-F 10% integer cap, uncertain/not-sent duplicate, boundary prior-epoch refund, 8MTU pacer and fresh independence, pending completion timeout/backward clock, invalid configuration/candidate/tunnel. These are first-party unit truth, not load test.

**Integration deferred to M0:** global 32KiB/s absolute allowance across different tunnels/clients and shared quota allocation, actual OS partial-batch dispatch outcomes, actual wire byte lengths/MTU, real retry admission and pacing scheduling, networking and Go V4 admission. No product/performance/physical qualification; RECOVERY_ENGINE_READY stays false. Code SOURCE Action to be observed after S, results appended to evidence receipt separately before H.

## Observed Actions for frozen budget SOURCE 4f485269b3af4b1aba46cce602a3996a720c8538
- [M2 worker-native 38561012183](https://github.com/lly8666/wbd-next/actions/runs/38561012183), attempt1: SUCCESS (precompile build job115841787143 then consume job115841904084); **15/15 r2_ Rust unit tests**, comprising previous 8 + new 7. Binary SHA256 a8f63c13de18e2dce8331ab035c6347b3c113b262f85eaee09cb1c11dc51452f, test log SHA256 8a002a24c0ccfc692e6a2429835b92bcff4c9a020d51231ab88f72766df0fe0d.
- [Governance 38561012060](https://github.com/lly8666/wbd-next/actions/runs/38561012060): SUCCESS, scoped branch path attestation.
- [historical G2 scoped bootstrap 38561012041](https://github.com/lly8666/wbd-next/actions/runs/38561012041): SUCCESS, tests filtered to old scaffold, never borrowed for new R2 qualification.
- [R0 static audit 38561012396](https://github.com/lly8666/wbd-next/actions/runs/38561012396): SUCCESS; not product proof.

Exact-source runner artifacts and hashes are frozen in docs/evidence/M2/R2-M2-BUDGET-001.json. No network, performance, physical, actual multi-client shared quota, or Go V4 production was tested. No additional feature follows this bounded atom.
