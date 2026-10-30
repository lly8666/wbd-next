# PLAN027 H528 — actual source7a four-tier damage, real F/R/C, no false PASS

H525 gate [41064405693](https://github.com/lly8666/wbd-next/actions/runs/41064405693) success. FOUR separate signed original Windows NPF/Wintun↔Linux Rust WSL2 TLS kernel 50Mbps/side,150ms/side,60s Actions all **real measurement and owned Stop PASS**. Exact immutable build SOURCE `7a5d7e83823e96539d2a904a8193a85ec18df30d`, H520 product build [41060763175](https://github.com/lly8666/wbd-next/actions/runs/41060763175) reused. Harness head is `a5b92619f8b18cbf0b05906bc808f276492a3d92`.

| Loss | Action | First Windows/Linux | Windows F / R / C (bytes) | Linux F / R (bytes) | True kernel eth0/ifb drops | Whole Win CPU 1core avg, peak RSS |
| --- | --- | --- | --- | --- | --- | --- |
| 1% | 41064427699 | 0.990188 / 0.989709 | 421585821 / 4972 / 2680 | 415912998 / 3757 | 4071 / 4250 | 9.236% / 50270208 B |
| 5% | 41064431346 | 0.949903 / 0.950019 | 421588735 / 2764 / 2721 | 415906393 / 0 | 20786 / 20648 | 10.066% / 50241536 B |
| 10% | 41064435483 | 0.901066 / 0.899992 | 421589817 / 2747 / 2290 | 415905463 / 133 | 41096 / 41290 | 9.362% / 50647040 B |
| 30% | 41064438830 | 0.701043 / 0.700934 | 421680421 / 1638 / 2422 | 415891317 / 328 | 124108 / 123465 | 9.038% / 50462720 B |

Windows actual frozen R is **strictly below 0.10F**, and ratios `R/(F+R+C)` are in exact JSON; Linux C not extracted so no invented Linux total ratio. Every NPF/TUN Stop succeeded; real repair sends existed in 1/5/10/30, but they are **only 3–6 Windows packets and 0–3 Linux** per 400MB first-source cohort. This is an authentic optional chance, **not substantial loss recovery**, and first delivery tracks configured loss. High 30% first≈70%, no bogus lossless repair. No one-way p99 claims, no cross-run Rust vs Go CPU gain, no 120s Auto downshift evidence here.

H527 [41065096863](https://github.com/lly8666/wbd-next/actions/runs/41065096863) gate and [41065096776](https://github.com/lly8666/wbd-next/actions/runs/41065096776) governance PASS after H526 YAML failure; seven A/B real Actions registered and still in flight. This report does not close A/B/C or task.

```feature-impact
{"kind":"none","ids":[],"reason":"Real exact-source native damage evidence/cursor only. No product, configuration or feature card changed."}
```
