# H2560 — accept H2559 historical weak AB and advance pre-EDT BBRv3

Six runs ended, five complete AB and one incomplete A at3% C (actual application recv TimeoutError). 24 ZIP CRC clean, six client/summary and client/server manifests identical, exact source/arch verified, all 18 capture receipts valid with zero kernel capture drops. 11 measured hash/EOF, all12 joined Stop, all six Rust natural retirements; both endpoint ingress full/Shared-TUN queue full zero. Full data: docs/evidence/M0/20261128-L2-WEAK-HISTORY-H2559-RESULT.json.

First60s Mbps A/B: 37.43/23.32,18.55/15.03,17.52/6.87 for 1/3/5%; A/C:56.38/5.26, timeout/18.27,11.08/19.92. C has severe slow 1% and faster 5%, not consistent seed regression. B Rust final inner retrans 15.87/13.93/9.10%, C 6.95/16.26/23.28%; these differ from outer netem target and cannot be equated to avoidable retrans. B late cwnd median 3.87/1.96/1.24MB, C 0.67/2.47/2.51MB. No local queue-full evidence; first data and RTT not equal across different runner groups. Earlier H2557 used 180s, not directly comparable to 60s. Do not claim BBRv3 sole cause before controlled comparison.

Next chronological candidate D exact cdd60c2d554a469db1dcb19351e88ebe4d65239b (native run46134184084 artifact15259306040), BBRv3 seeded75MB/s server service epoch/client0 ACK2, before EDT and ready-only GSO. Three independent 60s A/D 1/3/5% exact H2559 fixture; same old splice, no duplicate B/C or rebuild. Three triplets only. If D materially regresses, same-binary seeded BBR1 vs BBRv3 is required for causal discrimination; if not, advance to earned EDT and subsequent candidates. No production code/default/wire changes, L2 OPEN.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Archive six historical 60s weak AB receipts and run next exact pre-EDT seeded BBRv3 candidate."}
```
