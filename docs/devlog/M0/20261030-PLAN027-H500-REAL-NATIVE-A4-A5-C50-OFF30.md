# PLAN027 H500 — genuine H499 A4/A5/off30 FAIL and C50 PASS

All scenarios use H494 real `SOURCE 787ad4c900f3bae867c5c9556c4702339deef8cb` product and same original TLS/NPF/Wintun/Linux owner, downloaded immutable binary action [41025962277](https://github.com/lly8666/wbd-next/actions/runs/41025962277), independent Actions on harness `bdc9d4cb`. All artifact ZIP hashes/real counters in [H500 evidence](../evidence/M0/PLAN027-H500-A4-A5-C50-OFF30-NEW-SOURCE-20261030.json).

[41029396030](https://github.com/lly8666/wbd-next/actions/runs/41029396030) C50 Normal/off two-way 50Mbps each/25ms/0% 60s PASS first100% each, owned Stop and original Linux TUN/fq drop0; Linux opportunistic R1299B incidental no-loss, Windows R0. Source-true C100 11 missing H497 still strict FAIL.

[41029399148](https://github.com/lly8666/wbd-next/actions/runs/41029399148) A2 Normal/off30 true netem 10Mbps each 250ms/30%,60s: Windows first70.1962%, Linux first70.1991%, Stop PASS but **outer R=0, candidates=0 both ends**. Windows F86383225B, R0,C1143B (R/F=0, R/(F+R+C)=0); Linux F84987217B,R0 (real C exists). Actual 30% losses demand live ACK trigger diagnosis (Linux native outgoing ACK hardcoded1, no SACK capability cold negotiated, shadow-first outdated). No false target lower bound or synthetic repair.

[41029388055](https://github.com/lly8666/wbd-next/actions/runs/41029388055) A4 240s, actual staged tc 0→5/15/30→0 at 0,20.453,40.484,65.531,95.593s; first Windows100% Linux99.7028%, Linux authentic valid quality downshift profile5→0 revision6 and Windows profile2 revision4. **Action FAILED**: `WL_REAL_LINUX_OWNED_STOP_REQUEST_FAILED code=1` despite later Stop marker/report PASS, not qualified whole A4 120s both-direction.

[41029401961](https://github.com/lly8666/wbd-next/actions/runs/41029401961) A5 same-VM sequential B→A: B first100% both/owned Stop PASS CPU12.6056s per delivered GB; **A Windows product exited rc1** during required 60s, Stop NOT_RUN, no valid A/B CPU comparison.

Game2 highest FEC 41029390768 and Game4 highest 41029393488 IN_FLIGHT at H500; collect results, do not re-dispatch. PLAN027 §0 **PARTIAL**; ACK live repair, native Stop and A5 failures must be fixed/regressed; B lifecycle and C 300s/other tiers outstanding. No actual product code changed in H500 evidence batch.

```feature-impact
{"kind":"updated","ids":["fec-auto","linux-raw-tun","outer-opportunistic-repair"],"reason":"Source787ad4 C50 new product native pass, staged Auto valid grade but true Stop failure and off30 true outer repair R0 failure; feature verification scopes updated, no all-task PASS."}
```
