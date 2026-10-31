# PLAN027 H632 — Game FEC deferred batch RX wake/lane fairness

Review of H631's exact Wintun backpressure owner identified two related correctness hazards. Once a retained FEC batch completes, its Npcap event had been excluded from the previous turn's wait set. Calling INFINITE wait before re-arming that recovered lane could strand subsequent legitimate Game packets. A blocked lane at the head of the original early-Go TLS queue also held healthy siblings behind it.

H632 reconstructs the lane event set immediately after flushing bounded FEC retries and rotates only the already queued early records, preserving independent original TLS lane fairness. The new logic does not reseal ciphertext, replay an authenticated PN, duplicate an already committed restored source, grant fresh DATA credit, or change Stop. No physical or original new-source native PASS is implied. A complete live FEC loss-and-recovery test remains needed, as does Game's separate shared Normal outer-retransmission integration.

```feature-impact
{"kind":"updated","ids":["game-fixed-fec"],"reason":"Keep original native Game FEC retransient-Wintun batches wakeable and prevent early TLS queue HOL across independent lanes after backpressure."}
```
