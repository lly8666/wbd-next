# W111–W113: Game2/Game4 fixed6, exact original ARM64, bounded remaining tests

2026-10-26 user: continue GameMode tests; **GameMode DOES NOT REQUIRE AUTO**. This work creates **no Game Auto**, no FEC or outer recovery code changes, no upstream role edits.

## Exact provenance and capacity decision

- Work branch `experiment/fec-network-tuning`. Source binary `e8b41fb49a74648e405bf23e4600e23c618596fe`; build [40260662919](https://github.com/lly8666/wbd-next/actions/runs/40260662919), attempt1, artifact `12623678360` ZIP SHA256 `04d209b7ef1e887af6599622aaf71efc34381451c847e844cf18c2006ae9708f`, native aarch64. Reuses binary; fixture change only.
- Public original-Go TLS Game2 or Game4; `game_fec=fixed6`, `repair_enabled=false`; require **both native readbacks repair_enabled0 / actual DATA retrans0**, distinct genuine FEC parity sent and separate first lane copies. No Game Auto, no outer ON qualification.
- Retain `capacity_stop=true` due W102 historical Game2 shared GE ~2.56/2.43% and high host PSI33.81%, W109 burst PSI38.49%, W38 oversized overload. **No higher bitrate**: run 1Mbps per direction (below previous W102 3Mbps) on separate ARM64 Action VM/job; never cross-VM claim CPU gain. If observed host stress, STOP escalation and classify limitation. No throughput ladder or random-seed resampling.
- Mathematical warning: correlated GE across all lanes invalidates independent lane `p^L`; low 1Mbps partial FEC group mix is **not same-load A/B** vs prior 3Mbps source8afc. Stage injection RNG still unseeded; fixture seed controls traffic only.

## Single scenario per run

| ID | Request | Immutable request commit | GitHub Actions run | Predeclared qualification |
|---|---|---|---|---|
| W111 Game4 clean quiet tail | `tests/network/fec-work/W111-Game4-fixed6-outeroff-real-quiet-tail-1Mbps-arm64.json` | `79fca037c8d1c931c2f6663ac80f31b34a5aa887` | [40268464615](https://github.com/lly8666/wbd-next/actions/runs/40268464615) | active18s → genuine no-probe 12s idle → resume15s, 75ms, real mixed UDP/TCP; quiet injected/received0, real resumed first arrival, readback and Stop; sparse 10ms cross-HOL NOT qualified |
| W112 Game2 fixed6 shared GE | `tests/network/fec-work/W112-Game2-fixed6-outeroff-shared-GE15Long-1Mbps-arm64.json` | `81bbb0127def5b0fd4781d51a008fd6f07b9859a` | [40268468985](https://github.com/lly8666/wbd-next/actions/runs/40268468985) | clean15 → 30s both directions shared `gemodel [3,17,100,0]` → clean15; **strict 1% UDP and small UDP max all 3 phases**, no silent weakened damage gate |
| W113 Game4 fixed6 shared GE | `tests/network/fec-work/W113-Game4-fixed6-outeroff-shared-GE15Long-1Mbps-arm64.json` | `3290f2da010fac740a53ce28924306e50e6f8923` | [40268472555](https://github.com/lly8666/wbd-next/actions/runs/40268472555) | same low-load GE and strict gate, separate Action VM; NOT same-VM Game2/Game4 CPU comparison |

**During submission:** all three Actions confirmed started and entered genuine `Real public TLS Rust raw TUN business` measurement step; ***result pending*** until completed run/attempt, uploaded ZIP artifact/hash, exact UDP/TCP first delivery and native parity/outer counters reviewed. Preserve failure/red gate as true failed 1% qualification, not retry random seed. Windows remains `TEMP_SKIPPED_USER_20261025`. Do not call a passing clean gate complete GE service success. Do not treat Auto as required GameMode task.
