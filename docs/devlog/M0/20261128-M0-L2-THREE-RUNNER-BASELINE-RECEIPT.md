# H2526 — exact-source three-runner clean baseline receipt

## Trigger and governance recovery

The user authorized a no-op version commit and fresh Actions. Empty commit `93a9ae9` retained the exact db76055 tree and did not trigger path-filtered product workflows. A workflow-metadata-only commit `7cc6742` changed only the two workflow display names, which triggered the existing native and three-runner workflows. The branch had retained the old M0-MIXED-MODE registry/cursor and lacked eight current cursor references; syncing the current main registry, cursor, M0 prompt, START_HERE, construction decision and referenced evidence (13 files) in `c67a1e5` restored governance. Feature catalog and governance-maintenance then passed.

## Exact-source qualification

Run 46105447590 completed successfully on x86_64 and aarch64. Both original-product Normal functional receipts matched application bytes/hash, TCP half-close, UDP echo, eight concurrent connections and owned Stop; raw RX drops were zero. M4 clock unit passed. ARM local 512MiB clean measured 340.20Mbps with zero sampled retrans; 15s source pause delivered 512MiB at 94.03Mbps with matching hash/EOF and zero sampled retrans. The same-host 0.5% weak ABBA reproduced the earlier a99be82→7cc comparison: A 65.731Mbps / 26.027 CPU-s/GiB / 0.5165% weighted retrans; B 62.909Mbps / 25.760 CPU-s/GiB / 0.5104%. Stop sample was not a retired flow, so recovery review remains required.

## Three-runner result

Run 46105447669 used three distinct native ARM64 machines, 1GiB per leg, 600Mbps offered, 400ms added RTT, Normal, outer repair on, MTU1160, zero injected netem loss, ABBA. All four app hashes and EOF passed; relay qdisc drop counters were zero. Critically, the workflow's actual A source was `a99be828` (pre-DRS), not the current authorized `db76055`; B `7cc6742` has the same runtime code as db76055. Therefore this is a useful diagnostic of the earlier DRS change, not the requested exact db76055→new-candidate comparison.

A averaged 325.177Mbps; B 301.226Mbps (-7.37%). Combined endpoint CPU was 28.50→28.125 CPU-s/GiB (-1.32%). Retired server-middle weighted inner retransmission was 2.5716%→2.4545% (-0.117 percentage points), with timeouts in both variants. Bare brackets were 279.11 and 295.93Mbps (mean 287.52), below both WBD means. Harness status is `MEASURED_REQUIRES_PATH_AND_CAPACITY_REVIEW`; no performance qualification or causal claim.

Eight taps were individually valid with zero kernel capture drops, but identity sets differ across the server→relay and relay→client transitions. Preserve the raw artifacts and do not call these differences physical loss without accounting for packetization/offload and capture-point semantics. Exact counts are in the evidence JSON.

## Next discriminating experiment

Fix the A reference in both `tools/m0_dual_rust_tcp_local.py` and `tools/m0_dual_tcp_arm_linux_parity.py` to exact db76055 build artifact from run 46102235913. B will isolate removal of only the high-RTT receive-window extrapolation term, retaining twice measured fresh consumption, OFO span and existing low-RTT behavior. Then run the existing dual-ISA native qualification, same-host weak ABBA and three-runner clean ABBA. No fixed receive-window/rate cap, no new feedback controller, no outer-wire change and no cross-flow HOL.

Evidence: docs/evidence/M0/20261128-L2-THREE-RUNNER-BASELINE-RESULT.json

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Record exact-source three-runner zero-injected-loss diagnostic and the next measured-growth experiment; no product performance promotion."}
```
