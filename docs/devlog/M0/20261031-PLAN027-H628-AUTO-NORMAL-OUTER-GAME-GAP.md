# PLAN027 H628 — Auto and Game outer retransmission audit

Windows Auto already shares Normal's immutable M1/M2 frozen outer repair and NPF driver receipts, but auto_low_rate_mode skipped actual outer ACK/SACK gap hints and the shadow timer. Both skips removed in production, preserving Auto Quality/FEC and no additional Go worker. Original source-locked Windows/Linux weak-network test still pending, not PASS.

Game2/4 native owns TCP presentation ACK ledger and GameAdapter duplicate/FEC scheduler; it does not currently bind Normal's per-lane outer ACK index, frozen ciphertext shadow, global byte quota and real NPF retransmit settlement. Game sibling copy is NOT Normal outer retransmission. Next integrate shared Normal owner per authenticated Game lane and prove with real 30% loss/Stop; no fake pass or blind old FEC rerun.

H627 new-source Normal/Fixed 106s native Actions 41199245325/41199819746 were cancelled by independent deadline, not product PASS.

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Auto returns to the already shared original Normal outer ACK/SACK feedback and frozen shadow timer; Game integration separately open."}
```
