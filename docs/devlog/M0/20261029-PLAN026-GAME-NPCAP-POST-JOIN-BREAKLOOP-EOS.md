# M0 PLAN026 — Game2/4 real Windows↔WSL2 live-Npcap first read -2 after Go joined readers

2026-10-29. Exact signed Windows-Linux public source 6a8aa79d31a7f832c0dbe2dd5bb52c4cae5b41f0 [Action40846416052](https://github.com/lly8666/wbd-next/actions/runs/40846416052) **FAIL**: Normal/off PASS, Auto PASS, Fixed (true UDP/TCP/Stop PASS but M2 mature marker old missing) FAIL; all Game2/4 and Game2/4-FEC failed before Windows client Ready. New fail-only native Rust log proves the first true failure: `M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=RX stage=npcap_read lane=1 reason=EndOfStream`, followed by RX then TX exit rc=3. This is NOT a regression attributed to Normal, which remained PASS.

Root cause in original Go cold handoff:
- `m0_native_v4_game_rust_peer_windows.go` explicitly closes ingress and **waits for every original Go Npcap reader** before moving each capture.
- The shared `NpcapEndpoint.TakeNativeCapture` still unconditionally calls `pcap_breakloop` on its live pcap_t, even when no reader exists. Libpcap breakloop `PCAP_ERROR_BREAK` (-2) remains pending until the next `pcap_next_ex`; the first reader to consume it is now Rust, which legitimately treats -2 as EOF and fails closed. The real Action shows exactly that first-read -2.
- Fix: only after `p.readers.Wait()`, Game invokes a `TakeNativeCaptureAfterReadersJoined` method that reuses the exact same original owner gate/lease, DLL, pcap_t, NPF driver and Stop but **does not issue a new pcap_breakloop on an already quiescent capture**. TX-only new captures likewise have no Go packet reader to interrupt. Regular `TakeNativeCapture` still calls breakloop for active Go→Rust Normal/off and Fixed/Auto paths; these passed and are not reworked. Rust retains strict real -2 EOF and INVALID/AEAD/PN fail closed; no retry/ignore of an actual dead driver.
- Both authoritative original-Go `r0/go_overlay/assembly/manifest.json` and Windows `manifest-plan020-m0.json` pin the new platform and Game caller blobs. No per-packet Go FFI, new worker, Go data processing, protocol change or recovery gate.

The earlier Fixed source4c6a7c0 product patch sends a 1Hz **typed real original Rust M2 mature readback**, not fabricated Applied, with nine negative tests; its Windows WAL and full public Action are separately in-flight. The current Game handoff source must pass exact new Windows Go+Rust assembly, signed Wintun OS WAL and real Windows↔Linux Game modes before treating this root cause as fixed. Do not inherit b222 scoped PASS to assert full Game throughput, FIN/Dormant/Wake, CPU or physical PASS.

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Actual original-Go Game2/4 Npcap cold handoff changes live RX quiescent breakloop semantics to avoid one-shot EOF; source-locked platform/Go manifest and original TLS/driver tests required. Normal/off existing active-reader handoff remains unchanged."}
```
