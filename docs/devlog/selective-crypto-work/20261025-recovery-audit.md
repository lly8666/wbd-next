# 2026-10-25 recovery / completed negative experiment documentation audit

## Remote cursor and interruption recovery

Fresh remote branch HEAD at start: `126052adb1c59e5fe7c4baf06a37683c59cadcf0`; main HEAD `d8ba2cf270ff6ca5cadae6dab778c49c32636ef6`. This was the completed 2026-10-24 experiment closeout, not an unsubmitted patch. No mounted local Git repository was present in this session, so a local `git status` cannot be asserted; verified remote HEAD, committed content and exact run receipts through GitHub. No source code patch or fresh runtime execution took place in this recovery.

The permanent status at start already said `COMPLETE_SCOPED_NEGATIVE_PERF_BENEFIT_APPEARANCE_REGRESSION`, `open_requests: []`, `next_action: NONE_SCOPED_EXPERIMENT_CLOSED_NEGATIVE_DO_NOT_INHERIT_NETWORK_FEC_ACTIONS`. Checked all six relevant Actions finished SUCCESS: ARM64 S0 `40108785993`, x86 S0 `40109345476`, ARM64 AES128 S1 `40109817134`, constructed lab capture `40109989226`, native netns retransmission first capture `40110713400` (historical incorrect source-label receipt preserved), and native netns provenance correction `40110917872`. No need to re-run or modify any Action, and no outstanding intent to recover.

Evidence and limits unchanged: normal one lane/FEC OFF, explicitly enabled experiment Cargo feature only; S0 native component tests 157 PASS/0 FAIL/1 IGNORED per architecture; S1 real TLS 1.3 ciphertext, ideal oracle, single ARM64 job with six A/A-layout/B legs and frozen binary: record CPU B vs A savings 29.473239%, not total tunnel CPU; original controlled loopback and then genuine Linux netns kernel inner TCP retransmission prove repeated continuous 64/128B ciphertext at distinct new outer TCP Seq offsets. Native duplicate input interarrival 207.223ms, real Go→Rust→raw/TUN never qualified. Production defaults, authenticated bootstrap capability, generation, Stop, real business p99/first delivery, queues/drop, host capacity and real classifier remain UNTESTED; S2 heavy tests intentionally stopped on appearance regression, not marked FAIL or HOST_CAPACITY_LIMITED. All raw pcap/cert material remained owned temp only and Action artifacts contain summary/hash.

## Correction of stale historical navigation (documentation only)

Discovered stale `docs/testing/SELECTIVE_TLS_CRYPTO_WORK.md` first paragraph still claimed the work was design-only, and `docs/testing/selective-crypto-matrix.json` top-level `status: NOT_RUN` although bounded component/record/capture sub-tests had occurred. These could misdirect the next takeover to restart completed work. Corrected **only experiment-owned documents**:

- `docs/testing/SELECTIVE_TLS_CRYPTO_WORK.md`: explicitly label completed negative conclusion, precise SOURCE, scoped CPU finding, independent appearance evidence and remaining product NOT_RUN; historical work instructions retained without serving as a new task. Commit `cecccf8b1ecd04c09cd3a9fad7d90e5de338778f`.
- `docs/testing/selective-crypto-matrix.json`: top-level status now declares scoped lab completion/full product matrix NOT_RUN, with `observed_subsets` referencing actual run IDs and a note that `cases[].result` still refers to complete planned scenarios. No wholesale promotion of unrun S0/S2/S3 product cases. Commit `52446057d7004c3e82f12692d0ffc36365f96526`.
- `docs/prompts/selective-crypto.md`: add up-front post-closure guard explaining original prompt is historical authorization; no automatic new test or inherited FEC/network work. Commit `219ce153ec07c40e921224c40cc112e4fc963470`.

Neither original failed/mislabeled trace nor the successful follow-up was deleted or rebranded. Actual scientific finding and [final report](../../evidence/selective-crypto-work/FINAL_REPORT.md) stay unchanged. This recovery is not a new performance result, a new build, a product feature implementation, or a reopened experiment.

## Closure state

No pending Actions/intent; no new feature, workload, seed, hidden classifier, or product wiring. No main merge, production deployment, upstream role status changes, or branch force push. Maintain the existing `next_action: NONE_SCOPED_EXPERIMENT_CLOSED_NEGATIVE_DO_NOT_INHERIT_NETWORK_FEC_ACTIONS`. The scoped experiment is **closed negative**. 
