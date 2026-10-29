# M0 PLAN026 — real SOURCE578e Game2 pure TCP ACK first-error fix

2026-10-29. User supplied full 438-line actual native Windows Game2 step log for SOURCE `578e00d0c4e67746132fc8c64d28bdff100ac2ed`, [Action 40891615226](https://github.com/lly8666/wbd-next/actions/runs/40891615226); exact signed original Windows Go/TLS/Rust/NPF ↔ WSL2 Linux kernel (no simulated driver). Earlier user identified first Game2-only cold-run hang at SOURCEee2b Action#264, separate preserved historic result.

## Verified stage and actual first product failure

The independent real official Ubuntu 24.04.5 WSL2 guest boot stage was evidenced, and actual native step shows `WL_WSL2_STAGE_BEGIN actual_native_modes mode=game2`, `WL_ORIGINAL_NATIVE_E2E_CHILD_STARTED`, `WL_PUBLIC_REAL_MODE_START game2`. WSL iptables installed, exact Hyper-V owner allow, actual guest MAC verified and original Go NPF binding, true Linux eth0 TCP SYN and observed Windows NPF return PSH/ACK traces all ran. At ~46s: `M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=send_ack rc=1`, worker exit rc1, `WBD_WINDOWS_CLIENT_READY not observed`, `WL_PUBLIC_REAL_MODE_RESULT game2 FAIL`, `WL_ORIGINAL_NATIVE_E2E_CHILD_EXIT ... rc=1`. Uploaded step ends `WL_WSL2_OUTER_WATCHDOG_DISARMED`, `Process completed with exit code 1`: **not an unbounded Game2 process hang at this precise step**, although the workflow's final job/status may take longer. No Game2 UDP/TCP/Stop PASS.

**Exact source bug:** `crates/wbd-engine/src/v4_windows_game_native_runtime.rs::send_ack` sends a presentation-only TCP ACK using `wire_frame(...,&[])`. That calls `wbd-platform::ipv4_tcp::build_bytes` whose `measure(0)` explicitly returns `PacketError::EmptyRecord` (mapped `INVALID=1`). This is a deterministic wrong API call, not a driver error. An existing correct `build_presentation_ack` from the SAME first-party platform constructs a full genuine IPv4 TCP pure ACK, 40-byte headers, checksums, Windows persona and strictly no AEAD PN/record. This existing helper is already covered separately by platform tests.

## Correct minimal production repair and tests

- Route `send_ack` through a new bounded `presentation_ack_frame` wrapping `build_presentation_ack` into exact signed driver Ethernet envelope, original verified source/guest MAC, original seq/ack and same MTU; leave `wire_frame` and `build_bytes` **unchanged** for nonempty cryptographic records. Ack ledger only advances after actual Npcap `accepted_prefix==1`; fail closed on `error` or uncertain-prefix with typed driver diagnostics. No fake ACK, no empty AEAD record, no Go per-packet helper, no relaxed authentication/FEC.
- Add actual Rust Windows native tests asserting Ethernet + 40-byte control headers, seq/ACK/ports/PSH absence and that data builder still rejects an empty record; prove MTU rejects without scratch mutation. The same-source Windows Rust/Go and Linux Rust checks plus genuine Windows WSL2 Game2 real UDP/TCP/Stop must decide qualification. This is SOURCE *code* only until its specific Action finishes, never promote historical FAIL.
- No CLI, GUI, default or mode-mask change. Game2/4 product status remains experimental until signed Windows↔Linux kernel UDP/TCP both ways and owned Stop. Future Game4, Game FEC, Auto and same-host A/B separate.

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Fix Windows Game2/Game4 native runtime ACK-only packet construction that deterministically rejected zero-length data records; preserve authentic signed Npcap send receipts and strict data-packet empty rejection. Update recorded source578 Game2 FAIL; follow-up same-source product PASS not yet known."}
```
