# M1 -> M0 · R0 ABI harness exact-count selector (R1-M1-WAKE-STOP-002)
2026-10-14; M1 revision2 epoch1. Root build/test harness outside M1 allowed paths.

Observed on exact M1 SOURCE `203eac4afef8497e485f9b7e9ed5116e2b3b73a8`: `worker-native-tests.yml` Actions run 38566785197 SUCCESS (18/18 native R1; 10 previous+8 new). However `r0-native-abi.yml` run 38566785047 consumer FAIL because `tools/r0_abi_bundle.py` checks `"3 passed" in result.stdout` on an **unfiltered** `r0_abi_rust.test --nocapture` test binary, which actually passed 21 tests (3 ABI + 18 R1) with rc0. Initial source (10 R1) showed 13 total; `"13 passed"` accidentally matched `"3 passed"`, masking this test-scope problem. This is not an ABI product regression observation but the R0 workflow is genuinely FAIL and cannot be called PASS.

Request M0 change shared harness / root workflow to invoke only intended R0 ABI tests (e.g. prefix filter `r0_abi_` and verify all three distinct exact test names plus count), keeping Go/C/size/feature0 checks; lock same SOURCE and revalidate before claiming R0 regression. Do NOT loosen count by searching arbitrary substring or deleting M1 tests. M1 will not write `tools/`, `.github/`, `Cargo.*`, `src/lib.rs`, or shared ABI.

A separate Governance run 38566785008 failed `control or source moved mid-audit` when M0 changed main during a live audit; next H must pass on its own source for CLEAN. This request is not an M0 merge permission and grants no extra M1 scope.

## Reconfirmation on final code SOURCE
M1 corrected stop/inflight race in `81cbc57ae97ea8664c70e3ade6ecc718cc08d5d2`; new worker native [38567433037](https://github.com/lly8666/wbd-next/actions/runs/38567433037) compiled once and passed **19/19** (old 10 + new 9). R0 native ABI [38567433175](https://github.com/lly8666/wbd-next/actions/runs/38567433175) again **FAILED** because unfiltered Rust test binary actually reports **22 passed / 0 failed / rc0** instead of the hardcoded `"3 passed"` substring. No M1 ABI entrypoint or Cargo/lock modifications; issue remains at the shared test selector. M0 please own exact-filter fix, not M1.

## New parity-atom observed worker branch discrepancy

On M1 parity initial SOURCE `cfaf19e705d1b7295ccb3bee95baa799ce1052b3`, native ABI Action [38598099978](https://github.com/lly8666/wbd-next/actions/runs/38598099978) FAILED its consumer after compiling; the Rust executable rc0 actually reports 31/31 tests successful. Main `tools/r0_abi_bundle.py` blob `c7a22ce51b6ab059a847a83de0a1570e533108b5` already filters `r0_abi_`, but worker branch has old shared blob `c2b42b64a5763fecd01385d150d56ab8d6a7cc97`. Please M0 coordinate a non-worker-owned shared harness update/rebase/integration rather than requiring M1 to modify `tools/` outside allowed paths. Worker native parity proof remains independently scoped; R0 ABI workflow is NOT PASS.

## Final parity-source repeat of same old worker-only harness failure
Exact SOURCE `20809638ba86eed25aee463a7bbba9a002761799`, [R0 native ABI38598602157](https://github.com/lly8666/wbd-next/actions/runs/38598602157) consumer FAIL with Rust `rc0, 32 passed, 0 failed` on unfiltered binary and branch-old `"3 passed"` string marker. Worker native [38598602128](https://github.com/lly8666/wbd-next/actions/runs/38598602128) independently 29/29 PASS. Request remains M0-owned; no M1 shared test/harness write.

## R1-M1-READY-BATCH-004 (2026-10-15)
Native `worker-native-tests.yml` [38667033577](https://github.com/lly8666/wbd-next/actions/runs/38667033577) exact M1 SOURCE `3460d4f4630da3bfb1d9a0cfc522158adc14645b` succeeded 39/39 `r1_` tests (new 10 batch). The distinct R0 native ABI [38667033555](https://github.com/lly8666/wbd-next/actions/runs/38667033555) consumer **FAIL**: compiled Rust binary test run returned rc0 and `42 passed`, but old worker-branch shared harness checks for literal substring `"3 passed"` in unfiltered output. Fixed main variant is M0-owned. Request M0 coordinate merge/rebase/update of shared harness or CI scope, not write from M1. This is neither an M1 Rust unit test failure nor a successful R0 ABI workflow.

## R1-M1-RX-READY-BATCH-005 repeated worker branch stale harness

Exact worker SOURCE `e0a9f64d5c17d8085c52f09a083b9689535f00d1` compiled native worker [38669368706](https://github.com/lly8666/wbd-next/actions/runs/38669368706) 51/51 PASS. The same-source R0 native ABI workflow [38669368889](https://github.com/lly8666/wbd-next/actions/runs/38669368889) **FAILED** because the legacy branch-local unfiltered root harness demands literal `"3 passed"`, while Rust ABI test binary returned rc0 and 54/54 PASS. Main already contains a corrected R0-prefixed selector; please M0 coordinate shared harness synchronization/merge. This failed workflow is explicitly NOT_PASS and does not authorize M1 root edits.

## Latest M1 006 observed root CI mismatch
At exact source d60a69312cc9878e3b09a1598280c89dfd4da6d8, worker-native run 38674812277 passed 63 tests, whereas old shared R0 ABI workflow 38674812438 failed after its Rust binary passed 66 tests. M0 remains owner of the shared ABI test selector and worker branch synchronization. Governance code-source run 38674812385 separately failed twice because main moved during audit.

## R1-M1-GENERATION-READY-OWNER-BENCH-007
At exact M1 SOURCE `0979314cacf8931a90840ad312dd50e9e2777d04` the native worker [38678588923](https://github.com/lly8666/wbd-next/actions/runs/38678588923) was **71/71 PASS**, but shared old branch-local R0 native ABI [38678588872](https://github.com/lly8666/wbd-next/actions/runs/38678588872) consumer **FAIL**, despite Rust binary rc0 **74/74 passed**. The stale "3 passed" unfiltered-output root selector requires M0 shared harness synchronization; M1 has no permission to change it. Scope owner component-P0 samples are source-attested in M1 evidence, but an isolated dedicated CPU runner and full ready-drain release benchmark require M0 CI ownership.

## R1-M1-READY-GENERATION-RELEASE-008 shared root harness recurrence
SOURCE `fc023fba5bc7c51d07868a3d64d5356596130f75` native [38682808748](https://github.com/lly8666/wbd-next/actions/runs/38682808748) **75/75 PASS**, including source-locked release TX/RX benchmark. Root ABI [38682808744](https://github.com/lly8666/wbd-next/actions/runs/38682808744) consumer **FAIL** because old worker-branch shared script matches unfiltered literal `"3 passed"`; its Rust unit binary in fact returned rc0 with **77 passed, 1 ignored**. M0 to synchronize root selector; M1 cannot edit shared tools/workflows. Keep root R0 workflow FAIL.

## Task R1-M1-OWNER-LOAN-STOP-INTEGRATION-009

Exact source `39e6dfc0e3d7dfec12af0c28849b36d8f82b23ed` worker-native [38688812162](https://github.com/lly8666/wbd-next/actions/runs/38688812162) 80/80 r1_ PASS, plus 3 unrelated R0 tests filtered. Root R0 native ABI [38688812106](https://github.com/lly8666/wbd-next/actions/runs/38688812106) **FAIL** although Rust binary rc0 **82 passed, 1 ignored**, due to old worker branch `tools/r0_abi_bundle.py` matching `"3 passed"` in unfiltered test output. Request remains M0-owned; no M1 root tool/workflow edit.

## New task R1-M1-BOUNDED-EARLY-RX-BOUNDARY-010 (worker source exact)
Native worker [38711805820](https://github.com/lly8666/wbd-next/actions/runs/38711805820) 88/88 scoped r1_ PASS from CODE `2ce58427f84a777bce6242f6803a5c82413b5fe2`. Shared old M0-owned root R0 native ABI [38711805900](https://github.com/lly8666/wbd-next/actions/runs/38711805900) consumer still FAIL on stale literal `"3 passed"` filtered marker while actual Rust unit executable returned rc0 **90 passed, 1 ignored**. The issue remains M0-owned, not modified by M1.

## M1 R1-M1-OWNER-MEMORY-READY-WORKPACK-011

Exact M1 source `0ec99ed0bd5706c9df54649c0b20e1b157ffd363` worker native [38997851983](https://github.com/lly8666/wbd-next/actions/runs/38997851983) **96/96 scoped PASS**. Old root ABI [38997852003](https://github.com/lly8666/wbd-next/actions/runs/38997852003) FAIL despite real Rust rc0 98 passed, 1 ignored: worker branch M0-owned stale hard-coded `"3 passed"` match against unfiltered unit suite. M1 cannot edit shared `tools/r0_abi_bundle.py` or root CI; M0 synchronization/request remains OPEN. This does not downgrade the separately source-locked worker native 96/96.

## PACK-011: R1-M1-OWNER-MEMORY-READY-WORKPACK-011
Exact final M1 CODE `89a3acb23616a46ecc65fc2dcd0b75182b6b482a` [worker native38998296147](https://github.com/lly8666/wbd-next/actions/runs/38998296147) **98/98 scoped PASS**, including unequal wire-byte parity service. Root shared R0 native ABI [38998296139](https://github.com/lly8666/wbd-next/actions/runs/38998296139) consume FAIL; real Rust unit binary returned rc0 **100 passed, 1 ignored**, old worker branch M0-owned harness still matches literal `"3 passed"` in unfiltered suite. M0 to coordinate root synchronization; M1 has no shared tool edit permission. Do not mark root ABI green.

## M1-012 worker old ABI root script remains FAIL

At final scoped SOURCE `3c2b079ab88676a5c9c62ffecb90e8ae2b735ac2` native worker [39006176250](https://github.com/lly8666/wbd-next/actions/runs/39006176250) **103/103**. Old shared root R0 native ABI [39006176237](https://github.com/lly8666/wbd-next/actions/runs/39006176237) **FAIL**: actual unfiltered Rust rc0, 105 passed+1 ignored; historical worker branch `tools/r0_abi_bundle.py` still demands string `"3 passed"`. Main M0 shared root script previously fixed, but old worker branch not synchronized and M1 has no tools/CI path permission. Keep failure and ask M0 to coordinate if required; no all-CI claim.
