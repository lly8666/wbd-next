# PLAN027 H714 — one genuine original kernel pulse rerun with same product binaries

Task R0-M0-PLAN027-FEEDBACK-AND-NETWORK-CLOSEOUT remains PARTIAL. H713 corrected just the C 100/300ms pulse-aware `first_delivery_ok_for_scenario` oracle, with pure positive/negative original evidence regression: Action41275345866 cheap tests **PASS**, original H699 Action41264542737 stays **FAIL** and its actual loss/Stop/CPU/drops unchanged. No protocol or runtime change.

Exactly **one** new 100/300ms bilateral 100%-loss *kernel* pulse 60s Normal 10Mbps/25ms original signed Npcap/Wintun↔WSL2 raw/TUN scene was dispatched by controller [41275408316](https://github.com/lly8666/wbd-next/actions/runs/41275408316) (dispatch **PASS**, not product), actual native [41275419791](https://github.com/lly8666/wbd-next/actions/runs/41275419791) plus separate watcher [41275426382](https://github.com/lly8666/wbd-next/actions/runs/41275426382), both **IN_FLIGHT** as of this log. Immutable real source compiled once `d0661a2e110b523ad06b311da23fc1b7291442ba`, binary build run41274450306, Windows original artifact13071196733, Linux original artifact13070622152; no new product compilation. Harness HEAD at dispatch `415ad28b305b751f134146f7b009a27b0c080d08`, existing scenario SHA `75e2f6aa2e3f8909872390641233db8bc0a27db78908773697c798c9ce7ec63e`. Exact original measured pulse/readback, all business first/unreturned probes/CPU/drop and owned Stop still must be collected. Do not promote original H699 fail, parent Action dispatch success or green pure oracle to native PASS.

Other necessary different scene Action H710 game2fec 41274450306 with watcher41274456331 and H712 Windows B106 Action41275015266 watcher41275020610 remain in flight independently on distinct runners. No same-VM throughput concurrency. Physical NOT_RUN; complete PLAN027 §0 A/B/C and delivery only after all product qualification.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked one exact 100/300ms real kernel burst native regression and independent watcher, with original product binary reuse; no new product, configuration or wire behavior."}
```
