# PLAN027 H635 — Game2/4 same Normal opportunistic outer ciphertext repair

The Game native 2/4-lane post-TLS worker has an independent GameAdapter sealed PN per authenticated original-Go-TLS lane, not the normal single-lane M1 pending ciphertext. Treating per-lane FEC parity or sibling Game4 duplicate copies as outer retransmission is incorrect.

H633-H635 bind the authentic native attached 2/4 Game lane identity to a per-lane immutable frozen ciphertext snapshot **only after the real Npcap first-send success**, and reuse R2 Normal's `ReceiptState`, `OuterAckIndex`, process-global `m2_global` shared repair allocator, same v3 sampled admission and global PPS, receipt scope, `reserve_frozen_submission`, and `complete_driver_prefix`. The exact original PN, per-lane TCP sequence and ciphertext are retransmitted; no fresh GameAdapter seal or new AEAD nonce. Each Game TLS lane uses an isolated pseudo budget tunnel key with the original server-authenticated group generation, sharing the Normal process cap and bounded Stop retirement. Unauthenticated outer TCP ACK or data-header ACK are only scoped hints for optional frozen repair; never Wintun Applied, Health, Auto Quality or Game FEC success. Authenticated Game Health kind0 advances its real TCP carrier sequence span without becoming DATA shadow or spending first-send repair credit.

H630-H632 independently fixed Game-FEC parity wait on M4 copied rows, and genuine Wintun temporary-full recovery of unique-PN decoded batches with rearmed RX and sibling-lane fairness. Original Windows/Linux true Game2/4 weak-network 15/30% source-locked network verification **NOT_RUN** for this new source; governance or Windows eligible compilation cannot substitute for actual acceptance.

H633/H634 were short-lived intermediate source commits before the feature declaration/card sync; H635 records feature impact for the integrated candidate.

```feature-impact
{"kind":"updated","ids":["game-lanes","outer-opportunistic-repair"],"reason":"Game2/4 per-original-TLS-lane byte-exact frozen ciphertext outer retransmission now reuses Normal shared M2 ACK/shadow/global allocator and Npcap completion; Game-FEC and copy modes remain independent."}
```
