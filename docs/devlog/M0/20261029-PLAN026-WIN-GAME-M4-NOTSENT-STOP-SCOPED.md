# PLAN026 H354 test-first native Game2/4 Stop truth and signed-Wintun scope

2026-10-29. Source `db2f0244`, Windows original Go TLS + signed Wintun WAL Action `40826643885`: **Fixed and Auto REAL RS16 missing-source and first+reverse PASS** on real kernel after the exact 150ms source/repair batch fix; then Game2 original first+reverse real signed Wintun PASS, but `StopCryptoAfterDriverDrain` returns Rust `STOP_INCOMPLETE=5`. Go test then hangs in `tun.Close` 8min because already staged per-lane GameAdapter M4 tickets were never settled and original group-owned Wintun holds could not retire.

The original Game test uses **Wintun ingress to OS UDP app**, not Npcap per-lane TX. No NPF `pcap_sendpacket` was attempted. Claiming copied=true to pass Stop would forge a driver M4 receipt. Correct fix:
- The original *server* bridge now loads the already-existing Rust `wbd_m0_win_owner_v4_game_m4_send_result` C ABI unconditionally after group join, as original *client* bridge already does, including GameFec off. It does not open a duplicate FEC runtime.
- New conservative `CancelUnsubmittedGameTickets(ctx,rows)` on both real authenticated groups passes `sent=false` for **exact original staged lane/PN/logical IDs**. This grants ZERO M4 copied, FEC parity, applied, CPU or performance credit. Only cold/test/non-sent tickets may use it; actual NPF workers must first join.
- The genuine Go original TLS signed-Wintun Game2/4 test accounts the not-submitted client and server batches after validating kernel first+reverse and before Stop, preserving both Rust M3 replay rejection and strict Stop assertions. Failure-safe defer settles any remaining never-transported tickets and stops both actual owners BEFORE deferred Wintun.Close, rather than six-minute Go test hang.
- Original Go assembly manifest updates the protected Game FEC M4 ticket bridge. No production AEAD/PN, Linux codec, source/repair FEC2 or 150ms expiry changes.

This patch repairs a real **test fixture Stop bug**, not proof of actual NPF copy. Real Game2/4 2-worker native Npcap/Wintun product still needs independent physical true NPF copy+Stop tests. Same-source Windows WAL after this commit NOT_RUN until CI completes.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix false missing Game M4 NotSent ticket settlement in real signed-Wintun-only test and unconditional original server Game/off receipt lookup. No transport behavior, copied receipt, feature policy or product success changed."}
```
