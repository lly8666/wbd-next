# PLAN027 H544 — recover real four-rate failure; small feedback-supported expansion and Game cold overflow

**Recovery:** main at `734d182e8d2c67e2dafd5fc59d0303d0cd647b6b`, cursor H543. Source100 `10001c7eefb52387a5c71aa71129b80418273ac9` true signed Windows Npcap/Wintun + Go TLS and Linux Rust raw TUN built once in original [Action41085178791](https://github.com/lly8666/wbd-next/actions/runs/41085178791). Reused exact Win product archive12991283388 SHA256:59262ba3 and Linux archive12991187722 SHA256:714f898a. Four independent original Action results all green true bidirectional business/Stop but **FAIL latest user R/F target on BOTH ends**:
| true loss | Windows F/R/C (wire B) | Win R/F | Linux F/R (wire B, C unexposed) | Linux R/F | Action |
|---|---|---:|---|---:|---|
| 1% | 86395085/84864/182323 | 0.098% | 85004364/84358 | 0.099% | 41087790680 |
| 5% | 86402829/614863/185164 | 0.712% | 85003688/493931 | 0.581% | 41087795350 |
| 15% | 86386432/1551666/164312 | 1.796% | 84996658/1738378 | 2.045% | 41087799226 |
| 30% | 86373931/1886200/142641 | 2.184% | 84988651/2218354 | 2.610% | 41087803404 |

All 4 runs actually 10Mbps per direction/250ms/60s with tc kernel drops 1008/1108, 5145/5214, 15591/15643 and 31555/31228, genuine TCP/UDP, both owned Stop, Windows peak RSS42–43MB. New user requires 1%=0.4–0.6%,5%=2–3%,15%=3.75–9%,30%=7.5–10% each direction. **Every rate is below minimum**; do not use green banner as proof. Exact original per-run artifact IDs, SHA256, true first, CPU/RSS, qdisc and Stop preserved in [H544 JSON](../evidence/M0/PLAN027-H544-SOURCE100-FOUR-RATE-TIERS-ORIGINAL-20261030.json).

**Small product change, no new framework:** H539 existing deterministic one-half of *feedback-supported* gap is still the only trigger. Each newly accepted candidate may now borrow at most **three** recent (50ms–1.4s) unmarked original indexed first sends (bounded reverse peek at most256 entries, no new timer, no full scan). One bit `followup_offered` in existing index ensures no repeatedly selected tail. Both Windows Rust native owner and Linux Rust original sender call the same pure indexed method, then existing `shadow.on_outer_gap_hint`, existing driver-result settlement, 10%-F byte/8MTU burst/once-only same PN+ciphertext, fail-skip and owned Stop. This is intentionally cosmetic: some tail packets might not be lost; never affects real application first delivery or low-rate Auto. New source must be built and 0/1/5/15/30 verified, and if ratios fail root-cause further; **not PASS yet**.

**Separate B blocker in same Go cold assembly batch:** SOURCE080 Game4 FEC original Action41079630362 FAIL pre-Ready; Game2 FEC41079626524 CANCELLED (never PASS). Linux four lanes transmit before Windows joins cold M4. The bounded 256-entry `m0GameInbound` early ciphertext queue previously *terminated the Go reader on overflow* while other real TLS lanes still needed readers. Change only optional detached prehandoff inbound full behavior to drop the extra record and continue reading; test capacity/FIFO/resumption, preserve queue bound, source/manifest result blob, real Go TLS and Rust M3. Do not misclaim this as GameFEC fixed until exact new-source two OS Game2/4 FEC independent Actions complete. Game Health idle/90s and Windows rotation remain distinct B tasks; other PLAN027 A5/C still pending.

A single new H544 SOURCE build starts one genuine 0% original signed both-OS scene. After exact source real Stop and no-loss R0, reuse its binaries for each loss tier in one Action each (may run in parallel on distinct VMs) plus separate Game FEC regression; no repeated Go/Rust full rebuild for these cases. Preserve every old FAIL and historical source in original files.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair","windows-native-transport","linux-raw-tun"],"reason":"Recover actual source100 four-tier under-target R/F, add one cheap real-feedback-triggered bounded triple-tail immutable shadow nomination in shared Rust and both senders, and fix only optional Game Go cold prehandoff overflow; no protocol, crypto, limit or driver ownership change."}
```
