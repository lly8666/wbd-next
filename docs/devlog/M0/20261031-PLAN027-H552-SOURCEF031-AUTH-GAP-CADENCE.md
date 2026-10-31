# PLAN027 H552 — real sourcef031 four-rate closeout, one bounded feedback cadence candidate

Recovered latest main `5359c950b7c7dfb3c94c807e2bff74fb81d65554`, cursor H551. Sourcef031 product is the *original signed* Windows NPF/Wintun Go TLS/Rust ↔ Linux Rust/TUN. One signed build [41155198489](https://github.com/lly8666/wbd-next/actions/runs/41155198489), original Win artifact13024188713 SHA256 0189db2d08258bd9614ccbb38270b4d20fb8cf7fde2636f7ba6fa0ea1c82da4d and Linux artifact13024594029 SHA256 8dc7f6a008b69a34b54ea6de6f854161b2ee1243003c4f58b755d7f1933bd7f8. Actual 0% original win F86398827 R0 C197430 Linux F85006002 R0 and true first/Stop PASS. H550 one-scene Actions business and Stop all SUCCESS, but latest user **R/F targets failed BOTH OS at 1%,5%,30%**, 15% both passed:

| true tc loss | action | Windows F/R/C bytes | Win R/F | Linux F/R (C unmeasured) | Linux R/F | user target |
|---|---|---|---|---|---|---|
| 1% | 41161004484 | 86398479/118567/189103 | 0.1372% | 85006842/99820 | 0.1174% | 0.4–0.6% FAIL |
| 5% | 41161005816 | 86395990/1099963/185447 | 1.2732% | 85004095/972983 | 1.1446% | 2–3% FAIL |
| 15% | 41161007405 | 86391203/4057215/167859 | 4.6963% | 84995983/3585072 | 4.2179% | 3.75–9% PASS |
| 30% | 41161009034 | 86378445/5066482/145264 | 5.8654% | 84988951/4141942 | 4.8735% | 7.5–10% FAIL |

Real 10Mbps each-way/250ms/60s tc damage, UDP/TCP first and owned Stop PASS all scenes, source exact both OS; Windows whole Go+Rust native CPU 3.7812/3.7344/1.7031/3.3906s per separate hosted VM, peak RSS 42–43MB, **no causal CPU gain claim**. Source/artifact digests, first fractions, candidate/accepted/burst statistics, Fixed30 and Auto240, C50 recorded in [H552 JSON](../evidence/M0/PLAN027-H552-SOURCEF031-RATE-FIXED-AUTO-C50-20261031.json). Actual Fixed30 FEC first Win99.9427% Linux99.9709%/Stop PASS; Auto240 real stage first ~78.5%/Stop PASS and valid Linux quality samples/one-rung down, C50 Normal 49.99Mbps first99.9984%/100% Stop PASS. Sourcef031 Game2/4 highest FEC 41161010440/11977 still IN_PROGRESS; preserve these two, do not dispatch duplicates. The H551 C50 workflow_run gate never appeared because installed after completion; **no C100/300s child**, do not invent them.

**One minimal shared Rust source candidate**: `ReceiptState.on_outer_gap_recent_followups` gets one `last_cosmetic_feedback_ns` timestamp, updated only on a real ACK/SACK gap which successfully found new immutable live cached shadow(s). One-time / >350ms genuine gap: nominate ≤12. Gaps at65–350ms: ≤8; more frequent: ≤7; same batch timestamp: original≤4. Original index scans only latest256 retained shadows with 50ms guard and actual hard expiry; separate genuine gap trigger `outer_ack` unchanged, no DATA PTO/blind resend/new protocol or timer/Go hot loop. All candidates remain once-only original PN/Seq/cipher with existing R≤0.10F/8MTU/sparse cap/global budget, actual driver receipt and owned Stop. It may raise real R/F; **projection is not evidence**. New-source core+true original0% then separate unchanged p1/5/15/30 Actions must qualify. Old 15% PASS/other3 FAIL preserved.

Windows Game Health authentic 15s/90s/idle/rotation, A5 same runner Go baseline early RC1, DNS/MTU/local lane, C100/representative weaknet/mixed/burst/long remain independently authorized and unfinished. No code budget or retry framework expansion.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair","linux-raw-tun","windows-native-transport","normal-off","fec-auto"],"reason":"Record sourcef031 genuine 4-tier rate 3 FAIL/1 PASS, Fixed30/Auto240/C50 scoped successes; add a single productive authentic feedback time stamp in shared Rust ReceiptState to nominate at most12 existing immutable one-shot shadows, no new protocol/limiter/timer, Windows/Linux both reused."}
```
