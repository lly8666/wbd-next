# PLAN027 H631 — Game FEC transactional Wintun backpressure

H630's parity quantum deadline change was built and exercised by native-functional Rust tests (Action 41204314544, engine/fec/receipt/normal all success). The FEC timer now sleeps until the real copied-row wake or bounded flight expiry instead of waking every millisecond on stale source-close deadlines.

Further source inspection found a real FEC loss-of-delivery path: the original per-lane AEAD unique PN and shared FEC decoder are consumed *before* the actual Wintun copied prefix. On `ERROR_BUFFER_OVERFLOW`, the native Game FEC worker previously called `finish_fec_group(..., copied < total)` and discarded uncommitted decoded outputs. Replaying the original record would be denied by correct M3 PN replay protection, and the FEC decoder may already have marked source candidates.

H631 changes only the native Game-FEC temporary-full path: keep at most one decoded batch per lane, each <=16 restored frames. Retry the exact missing suffix without opening/re-decoding the same PN or re-writing an already copied prefix; commit the shared Game logical-first and advance presentation ACK only after **all** original Wintun writes succeed. On explicit Stop, pending batches are released without false delivery. When no FEC backpressure exists, the original event-driven indefinite RX wait is unchanged. Native FEC results and actual 15/30% recovery remain **NOT_RUN** for this source.

H630 governance failed because product changes lacked a changed devlog feature-impact block despite a valid under-16KiB Auto feature card. This source records the actual impact; no old test is promoted.

Game2/4 true per-lane outer ciphertext retransmission still requires wiring the **same** Normal ReceiptState/OuterAckIndex and global budgets; GameAdapter's sibling duplicate/FEC schedule does not replace it.

```feature-impact
{"kind":"updated","ids":["game-fixed-fec"],"reason":"Windows Game FEC original unique-PN decoder outputs are now held across transient native Wintun capacity denial; Game 2/4 shared Normal outer ciphertext retransmission remains pending."}
```
