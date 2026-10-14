# M1 -> M0 · R0 ABI harness exact-count selector (R1-M1-WAKE-STOP-002)
2026-10-14; M1 revision2 epoch1. Root build/test harness outside M1 allowed paths.

Observed on exact M1 SOURCE `203eac4afef8497e485f9b7e9ed5116e2b3b73a8`: `worker-native-tests.yml` Actions run 38566785197 SUCCESS (18/18 native R1; 10 previous+8 new). However `r0-native-abi.yml` run 38566785047 consumer FAIL because `tools/r0_abi_bundle.py` checks `"3 passed" in result.stdout` on an **unfiltered** `r0_abi_rust.test --nocapture` test binary, which actually passed 21 tests (3 ABI + 18 R1) with rc0. Initial source (10 R1) showed 13 total; `"13 passed"` accidentally matched `"3 passed"`, masking this test-scope problem. This is not an ABI product regression observation but the R0 workflow is genuinely FAIL and cannot be called PASS.

Request M0 change shared harness / root workflow to invoke only intended R0 ABI tests (e.g. prefix filter `r0_abi_` and verify all three distinct exact test names plus count), keeping Go/C/size/feature0 checks; lock same SOURCE and revalidate before claiming R0 regression. Do NOT loosen count by searching arbitrary substring or deleting M1 tests. M1 will not write `tools/`, `.github/`, `Cargo.*`, `src/lib.rs`, or shared ABI.

A separate Governance run 38566785008 failed `control or source moved mid-audit` when M0 changed main during a live audit; next H must pass on its own source for CLEAN. This request is not an M0 merge permission and grants no extra M1 scope.
