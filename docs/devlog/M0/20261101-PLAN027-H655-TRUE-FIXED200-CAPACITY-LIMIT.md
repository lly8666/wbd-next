# PLAN027 H655 — Fixed200 truthfully capacity-limited, Stop passes

[Original real source11f Fixed200 native Action41219651031](https://github.com/lly8666/wbd-next/actions/runs/41219651031) (harness cfa277e9) used the same frozen Windows original signed NPF/Wintun Go TLS + Rust and Linux original Rust raw/TUN binaries as H641. Requested each direction 200Mbps, 25ms, 0% kernel loss, mixed 64/128/512/1200B for 60s, exact scenario digest 7d704293d883ae24fec2a661f86ab7d1e05fb0b3fca62c9373165912fcf8a677.

Actual Windows offered 199.2333Mbps, Linux offered **126.8313Mbps** only, first delivery Windows 103.8543Mbps (fraction .816586), Linux 90.7956Mbps (.525883). Linux sender CPU **92.089% of one logical core**, TUN TX **231651 real dropped packets**, RX dropped0; Windows NPF approx local dropped0. Whole Windows original Go+Rust EXE PID CPU49.7969s/77.718s =64.074% one core; peak RSS50,675,712B. Real bilateral UDP+TCP, original native Wintun/NPF, original Linux raw/TUN and **owned Stop pass**, but **no-loss first-delivery and offered target FAIL**. Native V2 verdict `CAPACITY_LIMITED_GENERATOR_OFFER`; cannot infer all loss attributable solely to VM. Fixed200 at present host is not a qualified product throughput, and no higher/delayed Fixed200 same-family trials will be dispatched. Previous Fixed100/0 60s and Fixed50/0 300s remain source-scoped PASS; do not invalidate other mode families.

Scope H654 newly authored Windows Game Rust bounded Stop remains uncompiled/unqualified at the time of this evidence and is unrelated to the frozen SOURCE11f Fixed C run. GameFEC Linux-only original native positive and Windows FEC/B106 real cancellations remain separate. F/R/C and synchronized p99 not normalized for this run. See [H655 evidence](../evidence/M0/PLAN027-H655-SOURCE11F-FIXED200-CAPACITY-LIMIT-20261101.json).

```feature-impact
{"kind":"none","ids":[],"reason":"Only measure and record actual source-frozen capacity-limited Fixed200 negative and stop higher same-family trials; no new product or availability changes."}
```
