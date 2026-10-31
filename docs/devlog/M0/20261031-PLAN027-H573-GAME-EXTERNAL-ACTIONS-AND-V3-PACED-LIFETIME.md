# PLAN027 H573 — original Game FEC stuck-run recovery and v3 paced FIFO lifetime

After cursor H572, exact frozen SOURCE525 signed Game2-FEC Action41170807537 remains native-step FAILED / workflow IN_PROGRESS, Game4-FEC Action41170809210 native-step IN_PROGRESS; their same-run Linux watchdogs were themselves CANCELLED at ~20m, and no final true Game FEC business/Stop PASS exists. On-run cancellation destroys its own independent watcher before the Windows/WSL job finishes; fix **orchestration**, not speculative FEC math.

Replace the same-Action watchdog with a separate `workflow_run: requested` Ubuntu Action, matching only original main `workflow_dispatch` native runs. It observes that exact Windows job and after 1200s attempts cancel then force-cancel 45s later. One guarded push-only recovery job force-cancels precisely the two prior stuck run IDs after checking exact historical workflow HEAD; neither is promoted to business success. Existing per-command bounded WSL file-backed child tree, process watchdog, native Stop and frozen SOURCE evidence remain unchanged. No extra measurement job in a scenario.

Shared one-shot v3 outer repair already uses an ACK/SACK send-order cursor + half-PN sampling and 32 immutable-handle FIFO (H555/SOURCE525). Concrete remaining weakness: its queued opportunity was discarded after **20ms** even while original ciphertext cache remained alive and existing byte tokens were merely temporarily paced. For **opportunistic_v3 only**, hold the one-shot queued handle at most 200ms or the original hard expiry, whichever earlier. Keep old v2 queue lifetime 20ms, existing 32 candidates, 8MTU burst, <=10%F epoch credit, one repair, no new timer/thread or candidate multiplier. Use one already-present direction-wide retry deadline at 5ms rather than 1ms for less pacing churn. Same Rust shared policy on Windows/Linux; driver completion still decides R, no performance assertion before SOURCE-locked real runs. Add pure event regression for the paced v3 lifetime and exact eventual retirement.

Feature impact:
```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Allow existing immutable one-shot opportunistic candidates to survive a bounded temporary BurstPaced wait without altering initial DATA, actual driver accounting or hard ciphertext expiry; Game Actions hard deadline is CI-only."}
```

PLAN027 §0 remains OPEN: new SOURCE compiler/0/1/5/15/30 evidence, original Game2/4-FEC PASS, Windows Game Health/idle/rotation, A5 and remaining B/C. No old ratio claims or physical PASS.
