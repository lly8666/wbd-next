# M0 WinXDP Game shared-slot scoped acceptance and Normal Stop race

Exact tested SOURCE 5a40cbdb48a8c0030884d0f0e9c6076e1e6bda17. Linux ARM64 Action 46095848862 all four scenes PASS (eight real selected-slot swaps per scene). Windows + same-source Linux x86_64 Action 46095848855: ten actual functional scenes PASS, Game2 Off 3/3 (28175), Game2 Fixed6 2/2 (18463), Game4 Off 2/2 (18894), Game4 Fixed6 3/3 (27629): 93161 total UDP echoes, zero missing/socket errors, maximum gap 47ms, 40 native promotions and matching server slots, exact port changes and retirement, one Wintun/WinXDP RX/TX lifetime per scene, both Stop. 400ms RTT, zero injected loss. Only Game2 H and Game4 Fixed6 F 9V45; 9V45 coverage gate FAIL, no performance A/B or physical WAN claim.

Normal Action 46095848893 functional Off 4, Fixed 3, Auto 2, 9V45 2/2/1. Off F artifact 15242984984: 4783/4783 same-socket receipts; joined Rust and WAL-restored marker actually present. Stop command canceled 1Hz RuntimeMTU read, returned context.Canceled, Go misreported drift and nonzero exit. Reuse existing Game cancellation-aware drift classification in Normal, check caller cancellation around cold readback; keep real live errors and cleanup result authoritative. Auto B artifact 15242788857: 4846/4846, two 125ms receive gaps at elapsed 18.031→18.156s and 18.422→18.547s, generation 1 before first timer due, adjacent send spacings 15/16ms and RTT 406/407→516ms. Not established as rotation defect, no relaxation of 100ms gate; retain worst gap attribution in future receipts. Update stale source-only tests to assert selected Health slot ACK and actual NIC index through configure callback; no protocol or appearance changes.

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Align Normal and Game cold lifecycle cancellation handling; preserve live MTU/WAL checks and exact Stop, no hot-path change."}
```

Historical governance cursor validation fails on reviewed PASS evidence; not modifying historical evidence or assignment on this experimental branch. Feature declaration added for this change. Current source tests NOT_RUN until Actions receipts.
