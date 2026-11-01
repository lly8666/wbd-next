# PLAN027 H702 — manifest correction to unblock one genuine due-send diagnosis

H701 native [Action 41266666129](https://github.com/lly8666/wbd-next/actions/runs/41266666129) failed **before building product**: original Go overlay manifest still carried the three pre-H700 `result_blob` values. Independent WAL CI verified the same assertion. This was not a new due_send_records product verdict and did not validate Stop.

Updated only these three Git-blob attestations, without changing the original Go legacy source or old `original_blob` records:
- `r0/go_overlay/internal/windowsclient/native_real_product_service_windows.go`: `7ab79fcde1e080babc096db2b7194b560a838a6c` → `742be1997939a5417c020e2c971aaf099c3256be`
- `r0/go_overlay/cmd/wbd-client/m0_native_v4_game_windows.go`: `a187e2b9b340f0fce22eb4d1427ce1e63ac5211d` → `8450b0863c5ad5d5d95ac72d7cbb5e3701998da7`
- `r0/go_overlay/cmd/wbd-client/m0_native_v4_game_rust_peer_windows.go`: `5095c582d93ea03cffd8282625dd1ac6f73b6855` → `859acb4599157ff1f5e5f1e591c8457a5ebed7db`

H702 single new source build uses unchanged H700 Rust/Go diagnostic bytes, the exact prior Game2/FEC6 1Mbps/25ms/0%/10s seed, with one source-locked original Windows/Linux native Action. No Game matrix, protocol change or timeout extension. Until genuine Action finishes, first due failure branch and native worker vs WAL Stop remain **NOT_VERIFIED**. Product task PLAN027 remains PARTIAL.

```feature-impact
{"kind":"updated","ids":["game-fixed-fec"],"reason":"Repair three stale original Go overlay manifest source hashes after H701 prebuild failure; permit exactly one same-code 1Mbps zero-loss Game FEC native diagnostic, no runtime semantics modified."}
```
