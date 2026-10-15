# M0 wave4 · accepted three workers; no M3 acceptance · 2026-10-15

M0 starts prior clean seq51 H `bb4885e04ff8c757bae4d8c240392c429797349a` Governance38676088530 SUCCESS. Registered main active M0–M4 registry revision2/epoch1 without role ownership expansion.

**Scoped previous role acceptance**:
- M1 `R1-M1-STOP-LOAN-GENERATION-006` SOURCE `d60a69312cc9878e3b09a1598280c89dfd4da6d8`, native63/63 Actions38674812277; evidence S6b6a57e Governance38675181709 SUCCESS, H32ddf6c5 Governance38675249682 SUCCESS; no trusted origin. Previous code compiler and shared root CI count failures remain historical FAIL.
- M2 `R2-M2-RECEIPT-REVERSE-SCOPE-005` SOURCE `6f19c7d6e6d14c755e3eb657845a8d47718c8f71`, native38/38 Actions38674780276; evidence S c4e69939 Governance38675017005 PASS, H eb2b0ffa Governance38675209267 PASS; pure caller-trusted reverse receipt scope only. CODE-S Governance38674780251 control-moved FAIL preserved.
- M4 `R1-M4-AF_PACKET-PREFLIGHT-006` SOURCE `34736c19eb4138938f8bc6a78a697e34bac2a641`, native52/52 Actions38674827100; evidence S 6144a2d3 Governance38675076585 PASS, H1034e282 Governance38675200151 PASS; actual cap negative syscall+inert protocol0 FD, no traffic. Old branch root count and code-S control-move FAIL retained.
- **M3 intentionally excluded from audit and acceptance** per user. Existing `R1-M3-FEC-MULTISCOPE-012` continues without edited goal, done_when, branch or allowed paths.

New assignments on unchanged registry rev2 epoch1 SOURCE **`395cff66ba94eecc87e8e4dbdcda230603919cdc`**:
- M1 `R1-M1-GENERATION-READY-OWNER-BENCH-007`: bounded old/new TX/RX generation ready owner + explicit source-locked component benchmark, no fake Go auth or driver.
- M2 `R2-M2-REVERSE-GRANT-OWNER-BENCH-006`: exact two-scope repair grant constraints + model/perf measurement, no cryptographic endorsement or peer ACK false claim.
- M4 `R1-M4-RAW-RECEIVE-CONTRACT-007`: strict Linux raw RX owner scope/classifier, test-only capability-gated isolated loopback if privileged, unprivileged EPERM mandatory; no ambient capture/product activation.

Worker branches are **not** automatically updated/started by registry edits; each worker must fetch current main, do only owned writes, implement its own code SOURCE + compiled-once native evidence S + cursor-only H and pass Governance. Main decision document is not available in their existing historical branch HEAD until separately fetched; do not put a non-existent main path into worker branch `context_refs`.

M0 current code SOURCE `57e12d28f91ca7f3c716645305150871f5e3eff3` native P0 component measurement run38676814337 PASS with actual source SHA and binary/artifacts, and all11/11 source Actions success. Actual P0 first-run observations are not a 500Mbps product test; detail in `docs/evidence/M0/P0-native-component-measurement-and-wave3-acceptance.json`. M0 owns actual Go V4 trusted owner activation, real AF_PACKET and P1–P3 gates.
