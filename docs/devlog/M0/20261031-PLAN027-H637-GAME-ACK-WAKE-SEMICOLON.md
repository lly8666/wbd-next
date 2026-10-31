# PLAN027 H637 — Game shared Normal outer compile counterexample

The exact H636 Windows library job 41205618119 failed at original Game RX wake sites: `if changed{let _=tx_wake.wake()}` lacks mandatory `;` after the let binding, even as the final statement of the conditional block. Both pure-ACK and authenticated-DATA hint branches now use `let _=tx_wake.wake();`. This is a compilation correction, not an assertion of real network recovery or Game FEC PASS. H637 Windows source test is pending.

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Repair actual Windows Rust compiler counterexample in per-lane outer ACK wake; no change to Game FEC or original ciphertext retransmission semantics."}
```
