# PLAN025 H315｜Windows N0 M2 batch first-fault and typed preflight

## Intent / dependency
Linux original-Go/Rust positive modes are established and are the reference. Exact new main SOURCE `9ed962ef8ddd` Actions [40627263146](https://github.com/lly8666/wbd-next/actions/runs/40627263146) passed cheap core, Windows Go/Rust, Linux Rust and original Linux product build; real Windows↔Linux Normal/off N0 initially passed protected TLS, Wintun/Npcap+TUN, bidirectional UDP and bidirectional TCP, but native Windows owner stopped ~64s into the requested 240s. Artifact `12789959039`, SHA256 `78dc11a357a48e94ef50ea9edc4ae2127596ae72f5c079023e9f667efc093877`. One machine receipt is `docs/evidence/M0/PLAN025-H315-Windows-N0-main-source9ed-fail-20261028.json`.

## First fault / distinction
`actual original NPF M2 batch completed=0 expected=4: original-Go private Windows Rust owner refused`. Bounded Windows local NPF ingress queue drop stayed 7 during measurement, Linux RX/TX and Stop progressed. Source stage failures=0; M2 firstsend batch reached4, fresh shadow occupancy ~489 <1536; observed whole Windows Go+Rust process ~23.532% of one logical core and peak working set ~42.9MB. This is product/ABI preflight vs Rust M2 report **unresolved**, not proven host capacity or Go ingress loss. Full 240s, Windows normal Stop and physical NOT_RUN/FAIL as applicable; the older 60s positive and prior 29s FAIL remain separate.

## This batch / why not rewrite
The original `ReportOriginalM2NpcapFirstsendBatch` returned an undifferentiated refusal for local preflight bad count/layout, invalid rows, noncontiguous serial or duplicate PN, hiding the earliest discriminating failure. Preserve all checks, owner/generation and original frozen ciphertext; wrap each local rejection with typed *nonsecret metadata reason*. Keep Rust ABI rc handling intact. Add pure table-driven Go test for valid/invalid/duplicate/outcome/serial-wrap, execute on Windows preflight before true product N0. Same exact main SOURCE compiled once in Actions; no blind buffer growth, no FEC/Game/Go Linux changes. The previously considered ACK-only filter is explicitly **not applied**: this failure occurred with zero measurement-period local queue drops.

## Status / still unverified
Code + caller diagnostics + test + workflow/manifest entry frozen together for Actions; do not assert fix until exact 64s case returns its first rejection detail. Recovered Linux reference and separate history preserved.

```feature-impact
{"kind":"none","ids":[],"reason":"Windows internal firstsend-batch typed failure provenance and regression only, no public feature/config/default/GUI change"}
```
