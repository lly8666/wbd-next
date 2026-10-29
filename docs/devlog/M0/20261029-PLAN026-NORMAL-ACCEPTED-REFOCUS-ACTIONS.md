# M0 PLAN026 H358 — Normal/off baseline correction and return to Fixed/Game/Auto tests

2026-10-29, main HEAD parent e0a2f735a4df733dab5af7f4d7d98636593b1c90. User clarified that Rust Normal/off is essentially wired and tested. We traced the erroneous unfinished task language to M0 cursor.next_action (H357), registry.goal/done_when, M0 prompt, 2026-10-28 PLAN026 initial design and the 2026-10-29 execution contract, not to a present real Normal failure.

Verified historical evidence already in repo:
- SOURCE055 `docs/evidence/M0/PLAN026-S2-source055-Windows-Rust-Normal-real-native-functional-20261028.json`: signed Windows Npcap/Wintun Rust-only Normal 2 workers; original Go TLS; true Windows↔Linux UDP/TCP and both owned Stop; FUNCTIONAL_PASS.
- SOURCEa123 `docs/evidence/M0/PLAN026-N0-sourcea123-Windows-Normal-300ms-10Mbps-240s-PASS-20261028.json`: signed Windows N0 240s at 10Mbps per direction /300ms each way genuine kernel /0% loss; scoped PERFORMANCE_PASS.
- SOURCE7fc `docs/evidence/M0/PLAN026-WIN-RX-WAKE-150M-SOURCE7FC3-ACTUAL-PASS-20261028.json`: signed Windows 150Mbps per direction /300ms one-way /60s, 0% tc; first delivery 100% and 99.989474% by direction, Stop PASS; scoped PERFORMANCE_PASS.
- Old ABBA CPU rollback and capacity/variance failures remain honest source-scoped. No assertion that latest HEAD or physical PC has been revalidated, nor that all higher bandwidth/CPU improvements PASS.

Correction: **No Normal/off reimplementation, N0 replay or old-Go/Native A/B prerequisite before Fixed/Game/Auto**. Only impacted regression. Preserve all authenticated TLS/epoch/AEAD/PN/Npf/Wintun ownership/Stop guards.

Work resumed on actual remaining PLAN026: two exact-source Windows Actions gates now target Rust Fixed/Auto/Game native owner and Health replay, Windows original Go assembly, signed-Wintun WAL and mode/Health DLL exports. These build/FFI/core tests are not claims of full network/physical or FIN/Dormant/Wake qualification. Next locate first real failing job, fix only the actual first cause, rerun affected guard, then V2 real Fixed→Game→Auto+Health.

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Correct stale Normal/off progress to historical signed-driver and N0/150Mbps acceptance with exact sources. Workflow adds only Fixed/Game/Auto/Health core/ABI tests, no runtime change; unknown physical and newest HEAD scopes stay unverified."}
```
