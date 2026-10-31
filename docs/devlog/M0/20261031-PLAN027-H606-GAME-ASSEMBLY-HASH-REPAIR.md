# PLAN027 H606 — exact pinned Go overlay assembly hashes before real Game CI

H605 main original native [41189153926](https://github.com/lly8666/wbd-next/actions/runs/41189153926) correctly started but stopped in cheap `tools/prepare_windows_wiring.py --check-only`: `assembly blob mismatch: r0/go_overlay/cmd/wbd-client/m0_native_v4_game_windows.go`. Thus no Windows compilation, no driver/WSL execution and no Game business/Stop proof; H605 governance [41189153908](https://github.com/lly8666/wbd-next/actions/runs/41189153908) passed. H604 changed two Go Game overlay files and left source-frozen assembler hashes stale; this is test preparation, not a new product failure.

Update only their exact Git blob IDs in the existing pinned assembly manifest: game_windows `16a9d41c77b98be99e5245ab9abdcec002edd392`, game_rust_peer `5095c582d93ea03cffd8282625dd1ac6f73b6855`. No changes to original Go SOURCE, patch operations, driver, code, capture or watchdog. H606 push uses the original one-Game2 marker `[plan026-game2-only]`; preserve all earlier actual FAIL/CANCELLED. PLAN027 section0 A/B/C and Health/rotation remain OPEN.

```feature-impact
{"kind":"none","ids":[],"reason":"Only repair exact assembly hash metadata for the same H604 Go product bytes and H605 native CI staging; no product behavior/param/feature change."}
```
