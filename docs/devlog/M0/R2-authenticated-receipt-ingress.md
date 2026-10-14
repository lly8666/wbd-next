# M0 R2 authenticated receipt ingress and historical G2 selector — 2026-10-14

Atomic ID R2-M0-M2-INGRESS-001, M0 active main revision2 epoch1. Initial main HEAD 80856ab94c57245224c69c37ca207441b25da44b / M0 cursor seq26 checkpoint dc76aebd→HEAD one cursor-only H Governance38553161293 SUCCESS/CLEAN. No active CI runs/open PR. M2 independent head2cd993a seq2 partial, original implementation SOURCE7b02154e04b95452e40964c3b7d58368e534e0f5, native worker run38538225302 8/8 SUCCESS; issue#1 authenticated adapter and issue#2 G2 historical count. Current main G2 tool already uses `--exact tests::bootstrap_is_not_product_qualification`; verify it on same integrated M2 SOURCE before treating issue#2 as repaired, do not overwrite historical failure38538225378.

Why: successful ChaCha-only in-process first packet main SOURCE8731690 already binds real M1 unique arena, M3 Open, M4 read-only send. The next factual G2 interface need is typed backward Health receipt -> validated WBC4 -> M2 shadow under trusted lane+epoch scope, not a second fake cipher or a production Go V4 launch.

This atom imports byte-for-byte M2 worker `crates/wbd-recovery/src/lib.rs` and `receipt.rs` into main without moving worker ref; adds M0-owned `wbd-engine/src/recovery_ingress.rs`: requires caller-supplied already-authenticated reverse direction `LaneRxCrypto`, nonzero equal logical epochs, same verified lane; only actual in-place AEAD Open kind=Health can produce a `wbd_recovery::AuthenticatedReceipt` from bounded decoded WBC4 TLV. Direct raw control or header-only parsing cannot release shadow. Driver `submit_ready` Accepted/Uncertain/NotSent commits the original repair candidate without resending Seal or attributing syscall acceptance to peer ACK. Test uses M1 actual frozen and M2 actual shadow data, synthetic in-process sink and deterministic pre-supplied direction keys. **Admission trust origin is assumed at constructor, NOT cryptographically provided by Go V4 in this test**; any future construction path must be restricted to verified session mapping and cross-role key ownership.

Three required test scopes: authentic encrypted control releases original frozen payload; any tag error/wrong kind or wrong lane/epoch/key refuses release; candidate uses original frozen bytes and M4 outcome counts attempts without masquerading as receipt. Actions compile exact Rust1.85.1 x64 binary once, upload binary manifest, verify SHA and inputs in separate consume. G2 `--exact` historical scaffold must execute exactly 1 test even when M2 adds 8 r2_ tests; M2 native 8/8 and failed legacy G2 38538225378 retain independent source. Main ABIs feature0, product/performance/physical NOT_RUN, production Go V4 DISABLED, full encrypted live feedback, replay bitmap, global direction 1s repair budget, native raw driver and actual Go exporter NOT_RUN. No changes to config CLI GUI because internal test-only module, not an enabled user feature.

Next: after Actions, annotate M0 issues#1/#2 with exact scope, record evidence and cursor-only H; M2 next independent atom can proceed on pure R2 budget/2-send gate only after published verification and role writer checks remote cursor/assigned task. Do not tell user M2 production recovery is ready.

## Exact checked Actions outcome

The first integration source `40fb0d95e3101186704a6f38addab5eecc84cc51` retains explicit failed runs: ingress 38555876322, G2 38555876395 and native ABI 38555876452. Cause was M0-owned E0502 in the test's adversarial-byte indexing, fixed by a local length variable in S `29ebcb19863602ae1fc059fa3524837e90944da9`. No fail is relabeled.

At final test SOURCE `29ebcb19863602ae1fc059fa3524837e90944da9`, **7/7 triggered Actions completed SUCCESS**, no cross-source composition:
- r0-static-qualification-audit run38555987782 attempt1 success
- governance run38555987656 attempt1 success
- r2-auth-receipt run38555987945 attempt1 success
- r1-normal-off-chacha run38555987928 attempt1 success
- g2-scoped-bootstrap-native run38555987719 attempt1 success
- r0-native-abi run38555987729 attempt1 success
- r0-cross-abi run38555987832 attempt1 success

[True native ingress run38555987945](https://github.com/lly8666/wbd-next/actions/runs/38555987945) Rust1.85.1 x64 build job115825118023 compiled once; separate hash-verifying consumer115825415412 executed **3/3 PASS**. Binary SHA `648ded828e734f176864a83e446d2a7a37c78b549a7638a572c1158b5b141bac`; Cargo.lock `4147b1175268099e3f42a98bc23aeb08e762f24fa3d718a1d819322efa683b36`; test log SHA `b5e22c376b00ce15932c8b4ecf625e696d46eec5ba9db8591aa0701fecdc3b8d`. Build artifact11889368004, result11889198119. Historical G2 [failure 38538225378](https://github.com/lly8666/wbd-next/actions/runs/38538225378) stays FAILED. The current main's preexisting `--exact` G2 selector now passes with real M2 source at run38555987719; no worker ref has been updated. Main is ready for **scoped in-process adapter** only, not Go V4 authentication binding/production.

M2 resumption is contingent on worker-owned legal sync of current main to its branch, and a separately assigned pure budget atom. M0 will not force/rebase the worker ref. Eventual condition monitor must check this before alerting. Full receipt sender generation / reverse key from real Go admission / Rx replay policy / 1s budget / actual native network all NOT_RUN.