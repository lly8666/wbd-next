# PLAN027 H891｜Game4 OFF 与 Normal 同 VM R 成本的来源锁定功能卡登记

- H884 source `9fbb51e57a6183091b91516760c68c73c837934e`, Action41395887599 is a real same-Windows-VM/same-native-binary sequential Normal OFF→ON 10M each/250ms/30%/60s: OFF firstWin .703047/Lin .700815; ON firstWin .723679/Lin .724876; accepted Windows R=7,616,208B / F=86,376,838B (R/F=8.8174%, R/(F+R+C)=8.08996%), independent tc drops and both owned Stops. Windows whole EXE CPU OFF4.0625s ON3.7031s, **no isolated algorithm speedup claim**, two stochastic loss samples and cold startup/Stop. Exact source/results in H888 combined evidence.
- H886 source `e5f2e32977f3b4c6098c8ff2b1d957e0e00dd00f` Action41396919297: signed original Windows NPF/Wintun ↔ real WSL2 Linux Game4 4 authenticated lanes, FEC off, outer repair actual OFF readback on both, 10M each/25ms/5%/60s first .999988 both, genuine UDP/TCP + both owned Stop; Windows whole EXE 7.6406 CPU-s peak WS57,163,776B. Exact source evidence H886 JSON. **Not** Game4 highest FEC, 250ms30%, ON or physical.
- Updated `outer-opportunistic-repair` and `game-lanes` verified entries, with exact SOURCE and scope. Trimmed only already-obsolete historical candidate *limitations* where superseded by these directly measured natives; historical Git/devlog/evidence source preserved. Feature JSON stays within 16KiB cap.
- H889 source Action41399475839 actual managed105 and H890 source Action41399819159 original Normal ON 300s are independent and currently in progress at H891 doc writing. No performance or lifecycle PASS transferred from those pending scenes. H883 old source f361 long native job remains no end artifact as last checked.

```feature-impact
{"kind":"updated","ids":["game-lanes","outer-opportunistic-repair"],"reason":"Record original source-locked native H886 Game4 outer-OFF and H884 same-runner Normal ON/OFF measured scope without cross-SOURCE promotions; retain historic evidence."}
```
