# PLAN027 H676 — recovered real 5Mbps native PASS, 10Mbps fail is exclusively first 182 startup sources

[H673 original Windows↔Linux kernel native Action41236475558](https://github.com/lly8666/wbd-next/actions/runs/41236475558) successfully completed on same previously compiled ORIGINAL SOURCE `6ece9eab653f46a716e8d3a0927fb74bec4819e8` (H669 build run 41226521824 and artifact hash-verified, no new build). Real Windows Wintun requested MTU1280, actual Linux post-original-TLS TUN1209; both directions 5Mbps/25ms/0%/60s, exact original mixed64/128/512/1200B. Windows first **100%** at 4.9999Mbps, Linux first **100%** at 4.9986Mbps, original TCP, UDP, owned Stop PASS both. Product report artifact 13056465340 digest sha256:8ec648e2b587d2789252c56e933d4a2e49930ce13154013e42813ff183a59eca. True SOURCE/Harness separate manifest retained.

Read [H669 10Mbps original native Action41226521824](https://github.com/lly8666/wbd-next/actions/runs/41226521824) same SOURCE original report, not simply banner: at Windows receiver **first_received_seq 182**, **first_64_missing_sequence_ranges=[0,182)** and `missing_inside_observed_sequence_span=182`; after that no missing in 4096-source windows. Linux receiver 0 missing. Windows total first0.998172 <0.999, Linux1.0; true both Stop. H669 entire Action stays FAIL, 10Mbps not qualified. Pattern narrows to startup first deliveries (possibly receiver/driver readiness or early pacing) not steady-state loss; no unsupported attribution to precise layer or safe source-in-place symptom changes. 5M and 10M are different GitHub-hosted Windows VMs; no same-host causal CPU inference. Uncalibrated cross-OS one-way p99 still NOT_MEASURED. No second unchanged 10M seed.

H675 unrelated actual Linux Game2-FEC6 105s zero-business post-idle source-locked Action41236824445 still in-flight. PLAN027 remains PARTIAL with B/C and physical outstanding.

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Add real SOURCE6ece dual-OS MTU1280 5Mbps 100% first/Stop PASS while preserving same-source 10Mbps 182 missing startup prefix FAIL, genuine driver/MTU facts and distinct VM scope."}
```
