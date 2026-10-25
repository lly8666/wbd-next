# W31 FEC per-stream bounded parity scratch reuse

Base W30 standalone 220Mbps source W29 6246aa82: PASS but S2C residual0.977%, C2S0.850%; parity sent deficits2.52%/2.84%, jobs expired1398/1588, CPU PSI peak48.47, native TX worker CPU21.6s > RX16.6s full-run.
Current StagedParity::next_quantum() has 4 output Vec allocations plus one Vec of row views every <=4-row M3 batch; Maximum k16/r20 generates up to5 batches per full block, ~60k full blocks per side at W30. Heavy short-lived heap traffic competes for TX CPU and 10ms parity deadline.
New M3 method next_quantum_reuse encodes exact same final repair wire into four exclusive Vec scratch buffers owned by single FixedStream generation, resized only if symbol length changes. Borrowed stack-only slice array replaces temporary view Vec. Original M4 seal copies plaintext immediately into separate authenticated M1 arena; output scratch remains invisible to kernel loan, never changes actual AEAD PN, ciphertext, source priority, r/k, 10ms post-close age, or M4 prefix confirmation. Stop zeros scratch.
Existing public next_quantum method preserved for independent contract callers. Native product uses reuse method; regression Maximum k16/r20 compares ALL twenty wire rows byte-for-byte with independent scalar oracle before genuine M4 definite-prefix settlement; short/partial block old regressions retained.
Build exact ARM64 native once, run fixed/auto kernel recover regression. Then single scenario 220Mbps/side,30% IID,300ms one-way,600Mbps outer rate, real outer DATA retrans zero, same-VM A=W29 frozen 6246aa82 versus B=new frozen, sequential AB. If B business fails or CPU/Parity regression, mark NOT_QUALIFIED; do not retry seed, do not extrapolate >220. Preserve independent FEC branch and main/network role status.

## W31 finished observations
## W31 (2026-10-25): 220Mbps per-stream Parity scratch same-VM AB

Exact new source 3b16e79698d33ef49628dfa8f67a47550438ebbc native ARM64 build Action40146207152 PASS, artifact12580177860 ZIP SHA256 69c14dbc1f3a65040c7013844c02d6af036b4a238c6d78262f6edc65d891b30f. W31 reuses only four bounded plaintext Parity row Vec per FixedStream, eliminates one temporary Vec row views per quantum, zeroes on Stop; exact independent scalar full Maximum20 parity row comparison and real native Fixed/Auto TUN recovery PASS, original PN/M4 prefix untouched.

W31 sameVM sequential A(old frozen W29 6246aa82) then B(new3b16e796) Action40146429352 artifact12580747651 ZIP SHA256 cf2ec141c998ea3a0259be51c43e95f2971af3f56017d2e1a92e5e2d254eb667. Both request outer DATA repair OFF actually0; Fixed Maximum6 both applied, original fq600 test permanent neighbors, 30%IID/300ms one-way, rate220Mbps each, outer rate600Mbps, 15s warmup30s measure30s drain, source root/TUN drop0, native RX pressure/capacity rejects0, Stop full cleanup.

| Measure 30s each | A old (INCONCLUSIVE) | B new (PASS_SCOPED) |

|---|---:|---:|

| C2S delivered Mbps / residual |218.704 / 0.5991%|219.322 / 0.3226%|

| S2C delivered Mbps / residual |218.825 / 0.5467%|219.244 / 0.3526%|

| First p99 C2S/S2C ms |311.4/311.4|310.4/310.7|

| Source injector S2C send errors |2|0|

| Client parity planned / sent |1216620/1197346|1216772/1207605|

| Server parity planned / sent |1216630/1198153|1216724/1206714|

| Expired jobs client/server |889/864|424/463|

| CPU process client/server seconds |30.97/30.87|30.95/31.24|

| Host CPU PSI mean/peak pct |44.26/47.54|44.18/50.44|

Important: Entire W31 Action failure is A INCONCLUSIVE due 2 genuine injector errors (APP_SEND_ERRORS_OR_MTU_REJECTION), not B failure. A observed business residual values are descriptive only, not a strict A PASS. B both directions true PASS_SCOPED_OBSERVATION, parity sent ~0.75/0.82% deficit vs A 1.58/1.52%. CPU total increased 61.84->62.19 CPU-s, cannot claim net CPU saving; may reflect sending more parity, runner variance, unseeded netem and source A injector error. Host PSI peak B50.44%, so no rate above220 and no sustained qualification.

Next plausible bounded CPU work visible in original codec: PreparedBlock per-job table reference BTreeMap, per-quantum dynamically allocated src/dst slice views inside encode_prepared_into, and original authenticated M4 TX. Profile before replacing; no CPU overhead attribution without timing breakdown. Keep outer DATA retrans OFF, native Auto dynamic unfinished, merge_ready=false.
