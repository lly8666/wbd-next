# H751 — demonstrate actual Windows pipe blocked in diagnostic thread

GameFEC only; all unrelated PLAN027 remains paused, PARTIAL. H749 authentic original SOURCE0264 Game2FEC native run41289375904 and independent watcher41289383815 still in flight at author time.

H750 Windows2025 synthetic fixture run41289517226 FAILED: rc124 timeout and faulthandler Python thread stack produced, but only 3770 bytes arrived in unread stdout, smaller than assumed 4096. That did NOT prove OS pipe saturation and must remain a real fixture negative, not PASS. H751 changes synthetic wrapper only: aux diag worker executes continuous `os.write` into actual unread OS stdout pipe; one-shot supervisor stack must name `block_actual_output` at pre-timeout and actual stdout must contain at least 4096B Windows (8192B Linux). True native parent independently terminates owned child tree with rc124 in Windows ≤18s. This is a fixture failure correction, not a product ACK or GameFEC data-plane edit. Parent one-shot faulthandler minimum 0.5s for short fixture while real 250s dump remains 238s.

No Windows NPF, WSL2, TLS, Rust, Game worker or new product throughput claimed by this test. H749 real same-source run remains the only product test. Main governance and scope cards remain truthful.

```feature-impact
{"kind":"none","ids":[],"reason":"One synthetic GameFEC Windows OS pipe block rig and stricter Python stack proof after H750 honest fixture failure; no product modification."}
```
