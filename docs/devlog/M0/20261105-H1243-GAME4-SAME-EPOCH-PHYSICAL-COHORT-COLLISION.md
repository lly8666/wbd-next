# PLAN028 H1243 — fix SAME-EPOCH Game4 physical cohort misclassified as selected lane
## Authentic H1242 false CI PASS
Action42026936130 original native ARM64 Go TLS/Rust had green CI, but its ZIP21 sha256 492f597750e03322980563f325085720ab3b7f330028937fa3e34963826e07f0 CRC PASS revealed early SERVER stop: reason one-lane-native-rekey-failed, despite client Gen2 Ready later. Source .3→.9 physical+MTU1500→1280 occurred 2.815ms after old Game4 lane due, Gen2 M4 Ready after4.901s, Bob actual no-retry UDP54/75 with LAST echo4.762s BEFORE Gen2 Ready. Carol382/382. No broad universal PASS allowed. See docs/evidence/M0/PLAN028-H1242-SOURCEFD767-ARM64-PHYSICAL-HOTLANE-RAW-FALSE-PASS-20261105.json.
## Root and precise repair
Original protected Go logical epoch remains SAME during complete fresh physical A→B path M4 handover. Server previously branched into same-epoch hot ONE-lane replace merely on active old cohort, so full new physical group first authenticated TLS lane was mistakenly promoted as isolated lane, with subsequent premature server native-rekey-failed STOP. H1243 compares authenticated real TCP source IPv4 and original protected Client/ServerRecordLimits vs old member; new physical IP or smaller genuine record MSS -> stage COMPLETE 4-lane authenticated TLS group and only exact-stop older group after entire new Rust M4 Ready. Same physical IP+record cap continues previously proven Game4 one-slot rekey. No wire/FEC/algorithm change or second controller.
## Strict native scope
H1243 ARM64 both ends original pinned Go TLS+Rust, one Game4 Fixed6 representative with Normal control and kernel 120ms physical delay. Must have real due then OS source .3→.9+MTU1500→1280 before selected lane READY, 2 full Game4 server groups, server no early one-lane-native-rekey-failed, EXACT old Stop after whole new M4 READY, Bob UDP after new Ready+2seconds, Carol continual real correct UDP, original shared443, inner MTU1358→1178. Native SOURCE is NOT_RUN before Action. Historical H998 same-socket live MTU shrink FAIL and H1237 stable-path Game4 netem5 PASS unaffected.

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter"],"reason":"Repair protected same-epoch full Game4 physical cohort versus isolated lane classifier, mark prior H1242 green CI as false business PASS and require actual post-gen2 UDP."}
```

## H1244 Go native compile API visibility correction

H1243 [Action42041663138](https://github.com/lly8666/wbd-next/actions/runs/42041663138) original Rust compiled, but original Go `v4productcli` build hit 2 undefined `V4LinuxGameAuthenticatedLane.ColdSnapshot` methods before any native runtime. Correct with a narrowly exported `AuthenticatedRecordLimits()` that returns only original TLS/M1 verified Client/Server uint16 budgets, not protected private keys/epoch/owner. The new same-epoch full physical group vs same-physical one-lane source classification is unchanged, still native NOT_RUN. H1242 false-green Bob outage preserved.

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter"],"reason":"Fix Go M1 authenticated read-only record limits wrapper used by H1243 true source4/MTU group distinction; no wire/crypto change, native retry pending."}
```
