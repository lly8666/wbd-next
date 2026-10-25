# W38 findings

## W35–W38 2026-10-25: task-deadline-before-TUN / source symbol workspace / first packet-realistic 200Mbps A/B

Suggestion 1 verified: original TX worker called blocking poll(TUN,10ms) before checking owner 10ms post-close Parity and authentic M2 feedback deadlines. W35 source e2aeba7a fixed by computing nearest deadline before poll, waiting at most floor(time-to-deadline_ms) ≤10ms and zero if queued/already due; rechecks after poll. No new busy thread, M4 kernel proof/AEAD unchanged. ARM64 native PASS.

Suggestion 2 verified: each k16 FEC block used k separate Vec math symbols, despite already shared parity scratch and ISA-L tables. W36 source 861f0396 uses one contiguous zero-tailed k*symbol_len source workspace, reuses it across blocks only after synchronous true M4 copied-prefix settlement, scrubs on Stop, keeps Scalar/ISA-L math exact and first send unchanged. Corrected deterministic test expected 16*137B for mixed first-source135B plus15*77B block; native Fixed/Auto true TUN and Maximum20 PASS Action40150749260, artifact12582379708 ZIP SHA2565f9f587a4d1d44a3cf482c4c46a5be5b52cc71fdb4080935de153dc85f89f7e5.

Suggestion 3 examined: split ingress already exists for Normal/off using bounded channel512; Fixed/Auto intentionally keep one reader/TX. Under high host PSI do NOT add reader/thread without phase latency evidence; measured W38 shows product CPU and source TUN drops, so separate thread is not justified yet.

W38 same-VM real 200Mbps each, 96% UDP/4% two TCP socket, 35% count size64–256B and larger 512/900/1287B, 20Hz sparse64B probes,30%IID/300ms one-way, original outer600Mbps,fq600; first-arrival small actual application UDP cohort p99 and 10ms 300ms-delay-aligned gap, 15s warmup30s measured30s drain, real source zero-drop required, original outer DATA retransmission zero, authenticated M2. Action40150988880 FAIL both A/B, artifact12583045399 sha256 c90496f5f074082ac174de109d1830b3289f3f24d83ea61678e1df67d9cadb26.

| Metric | A W33 e99a4aff | B W36 861f0396 |

|---|---:|---:|

| C2S UDP residual |13.3746%|5.5686%|

| S2C UDP residual |13.7190%|6.3371%|

| C2S real small UDP<=256B residual / p99 |13.6155% /316.2ms|5.4765% /320.5ms|

| S2C real small UDP<=256B residual / p99 |14.0161% /316.2ms|6.3845% /321.3ms|

| TCP 8Mbps target each dir actual C2S/S2C |0.132/0.102Mbps|0.386/0.238Mbps|

| Client/server FEC jobs expired |40824/42260|14479/16998|

| Client/server Parity rplanned→rsent |1935490→1075756 /1932987→1042770|1926712→1628512 /1928128→1577641|

| Host CPU PSI mean/peak |43.48%/46.31%|56.57%/60.32%|

| Source TUN drops steady client/server |296/0|390/1017|

All outer DATA reTX0, RX decoder reject0 and RX capacity/pressure eviction0, exact native sender/rx recovered real TUN and Stop cleanup. CPU measurement in host process full-run (includes warmup/drain), not mislabelled 30s. Source drops and TCP backpressure explicitly disqualify. More FEC sent in B also raises CPU PSI, so don't claim stable CPU efficiency or full 200Mbps mixed capability. Lower effective app-byte target still increases packets/s enough to overload four-core runner. B improves parity deadlines but insufficient, do not extrapolate 250Mbps mostly1287B tests.

Size count distribution is illustrative workload (6/8/10/11/15/20/30 per 64/96/160/256/512/900/1287B), NOT externally trace validated representative Internet distribution. A 20Hz 64B distinct probe provides sparse small signal; W39 will provide true one-way first-arrival and loss distinct from RTT, at SAFE 100Mbps lower diagnostic after the W38 200Mbps capacity stop.

Status capacity_stop true, merge_ready false. No main or upstream network branch touched.
