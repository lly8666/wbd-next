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
