# PLAN027 H547 recovery — 4 rate failures, 2 Game cancelled, A5 inconclusive

Recovered main 1ed710f925e1157a8d589fc953c5933c0dcf6d97. Product SOURCE ba8d999aa806800cfb562ed34dfd738a98fb45bc. Four independent original Windows NPF/Wintun GoTLS + Linux Rust/TUN Action scenes all true business/owned Stop PASS, **latest user retransmission rate FAIL each side**:
| p | Action | Win F/R/C bytes | Win R/F% | Linux F/R bytes (C not measured) | Linux R/F% | first Win/Linux |
|---|---|---|---|---|---|---|
| 1 | 41126738290 | 86427592/93711/186339 |0.1084|85005791/85181|0.1002|0.990899/0.990849|
| 5 | 41126741528 | 86395653/623924/183017 |0.7222|85002852/530914|0.6246|0.953431/0.95228|
|15 | 41126744763 | 86388141/2333846/164726 |2.7016|84995026/2722070|3.2026|0.857088/0.857835|
|30 | 41126748120 | 86373103/3002017/144084 |3.4756|84989130/3349406|3.9410|0.712861/0.708966|

Windows whole original Go+Rust CPU2.7656/1.7344/2.0781/2.5469s, RSS42.856/43.110/42.500/42.770MB across independent VMs, **no speedup inference**. ZIP artifacts+SHA full in H547 JSON. Prior 0% Action41124773657 first100% both, R0 both, owned Stop. SourceBA8D p30 Windows quota_rejected=0, candidate_first3701 repair_accepted3508; inadequate feedback-motivated cache candidates, not rate ceiling. H544 chose recent PNs from outer ACK index, but positive/cumulative ACK had already retired their live ciphertext; extra selection also waited for OLD head shadow alive, starving newer candidates. H547 removes redundant ACK-index selection, directly scans <=256 truly live immutable ReceiptState shadows on real sampled ACK/SACK gap and selects <=4 age>=50ms still cached one-shot records. Allow stale old head as hint, never wait for it; original PN/cipher/seq, no new control, timer or limiter, R<=0.10F and Stop unchanged. New exact source real 0/1/5/15/30 NOT_RUN.

Game B sourceBA8D Game2-FEC Action41126751247 and Game4-FEC Action41126754244 both CANCELLED after WSL guest boot, no product PASS. Older Game4FEC source080 Windows Ready FAIL. Original Windows Go cold started TCP SYN then waited individually up to20s; H547 starts all genuine Game2/4 independent SYN lanes first, awaits each under ONE original 20s clock and 100ms tick, no steady Go pump. Existing early-M3 bounded overflow skip remains. Game modes on new source must be verified.

A5 sourceBA8D Action41126757601 FAILED: sequential same VM Rust B 60s true both first100%, owned Stop, CPU3.875s RSS41.88MB; Go A exited after14.219s RC1, Stop NOT_RUN, A5 INCONCLUSIVE. No CPU superiority claim, no repeated unexamined rerun. Full evidence docs/evidence/M0/PLAN027-H547-SOURCEBA8D-FOUR-TIER-A5-GAME-20261031.json. H547 Go cold staged exact assembly result blob3e7d942acafc46bb3f2a8b54a5d1df5d756fdc04; core unit test live one-shot shadow. One SOURCE build and true0% then independent affected tests only. Remaining Windows Game Health15/90, rotation, A4/A5, matrix C/mixed/long all OPEN.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair","windows-native-transport","linux-raw-tun"],"reason":"H547 sourceBA8D real all four loss-rate FAIL; choose <=4 actually retained one-shot Rust shadow candidates per genuine ACK/SACK gap, and parallel original Go Game SYN cold lanes; no new hot protocol, limiter or timer."}
```
