# M0 PLAN026 H353 — Windows Game2/4 native Rust 2-worker code batch

2026-10-29; source parent `ac384abe`. This is **actual production source candidate**, not only a plan, but no real network, driver, CPU, FIN or Dormant Applied qualifies until exact-source tests.

## One source, one owned native data path

- `crates/wbd-engine/src/v4_windows_game_native_runtime.rs`: V3 typed native 2/4 original TLS-scoped Game lanes. C ABI `wbd_m0_win_game_native_v3_{start,early,stats,stop}`. Exactly **one Rust TX and one Rust RX** thread for the group, sharing the one genuine M4 Wintun session. Each per-lane Npcap receive/send captures and original TCP serial boundary is separate. Wintun RX is only read by Rust TX; Rust RX authenticates by the existing GameAdapter unique AEAD/PN; GameFec uses the **same** Linux GameFecTx/Code/Reassembler, not a new codec. Game4 delayed replicas and parity call the existing adapter due scheduler, bounded polling 10ms. Per-lane real `NpcapTx.send_batch` driver prefix settles original staged `logical_id/PN` exactly once; NotSent/uncertain never create success credit. Rust RX calls original group opener, Wintun send and authentic TCP ACK ledger; invalid records never reach Wintun. Stop joins both Rust workers, returns every Wintun/Npcap loan before Go M4 Stop/WAL.
- `bridge_v4_windows_game_native_io.go`: original Go independently authenticated 2/4 TLS lanes **authorize** the V3 owner (group ID, TLS epoch and real OS LUID/ifindex), which original Rust registry verifies independently against the same group. Go only cold-starts, hands over, checks 1Hz native stats and joins. No Go per-packet callbacks, no duplicate native AEAD or GameFEC.
- `m0_native_v4_game_windows.go` transfers Go TLS's Npcap readers into the Rust Game native peer after group bind, preserves bounded early original NPF ciphertext for Rust M3 open; no more product Game Go business pulse. `m0_native_v4_game_rust_peer_windows.go` waits for real TX+reverse copy, verifies OS health at 1Hz, joins native before driver or Wintun close, no legacy fallback. `npcap_native_handoff_windows.go` exposes only read-only original native config needed to reopen send-only capture.
- Windows one canonical original Go source-locked manifest updated, no dual installer; rust native consumer is feature7-gated and rejects single-lane, mismatched original handle/epoch, missing drivers. Existing historical Go Game code remains compiled for source rollback/reference but unreachable from main Game product selection.
- Legacy PLAN020 CI exported mode-caps assertion was stale (expected Normal-only) even though actual original Rust ABI advertises mask31/4. Scope updated to check actual 31/4 but explicitly **does not count advertisement as native Game/Fixed/Auto functional evidence**. No weakening of real packet, WFP, OS or Stop admission.

## Pending further product work/tests

1. Confirm real source Windows+Linux Rust and original Go compile, resolve any compile/borrow/API mismatch at first failing test, then full 2/4 original Go TLS native Game M3 direct Wintun/NPF signed driver bidirectional/Stop, Game fixed and off, loss/delay 7 fixed profiles via W168 matrix adapted V2 24 fixtures.
2. Fully wire idle FIN/Dormant/Wake on original both ends and end-user keepalive interval/dead/idle config+effective readback. **Never** turn 90s authenticated death into server DORMANT. 15/90 Health already in Rust but this is not FIN-lifecycle complete.
3. Linux Auto 2s Rust migration and real M2 applied status, 1Hz CPU/RSS/threads and verified Windows/Go steady A/B (source frozen); Auto+Heartbeat/dead/FIN tests **last**, real 60s/90s idle durations rather than fake short timer evidence.

```feature-impact
{"kind":"updated","ids":["game-lanes","game-fixed-fec","windows-native-transport"],"reason":"Windows Game2/4 original-Go TLS-scoped one native Rust group, 2 worker Wintun/2..4 Npcap M3/GameFEC/M4 copied-prefix/Stop code candidate replaces Go hotpath. New physical, performance and correctness qualifications NOT_RUN."}
```
