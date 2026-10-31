# PLAN027 H636 — Game shared outer Rust worker return guard

Game2/4 native TX and RX workers return integer statuses, not Result. H633-H635 shared Normal M2 wire-up had erroneous question-mark propagation inside these workers. H636 replaces these with checked integer exits while preserving original NPF completion, Game ciphertext PN, Health kind0 TCP sequence, FEC Wintun delivery, and exact Stop. Genuine original-Go TLS native FEC 15% and Game outer weak-network results remain NOT_RUN for this source.

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Game 2/4 Windows shared Normal M2 worker error handling uses explicit integer-return checks; native product network evidence pending."}
```
