# PLAN027 H501 — live peer ACK minimal product correction (UNVERIFIED)

Observed native SOURCE787ad4 A2 off30 Action41029399148: true loss, first only 70.2%, driver/Stop PASS but both outer R=0 and candidate_first=0. Original Linux firstsend and repair TCP-looking carrier always advertised `ACK=1`; Windows could not nominate any real ACK hint. RX original `rx_anchor` is HIGHEST authenticated seq anchor, NOT a contiguous receiver ACK. H501 implements a bounded 256-range out-of-order `OriginalPresentationAck`, fed **only by original verified M3 LINK/control**, publishes a per-session atomic exact contiguous ACK consumed by existing original Linux raw DATA and retry; no Go per-packet work, no new PN, no unnegotiated SACK, no invented Receipt or protocol round. Original `OuterAckIndex` also forgot oldest metadata while its frozen shadow expires: prune **at most 64 spans older than 900ms per real feedback** before nominating 3-duplicate ACK one-send candidate. Once-only shadow quota and process R≤10%F remain untouched. Add unit source tests for contiguous and bounded prune; do not infer functional repair before real native test.

Same commit freezes new product SOURCE and installs a **one-shot** H501 on-push gate dispatching ONE new Linux+Windows build/real 10Mbps each/250ms/30% 60s original signed Wintun/NPF/WSL2 Action (all tests in Actions). H500 failures, A4 Stop, A5 Windows early exit, H497 C100 remain FAIL/NOT_RUN, Game2/4 H499 in-flight. Next consume actual SOURCE/run/hash/R/F+C/Stop and adapt only observed defect.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Scope minimal original Linux authenticated TCP presentation ACK and stale optional metadata repair; live native new-source feature NOT_YET_VERIFIED."}
```
