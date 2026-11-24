# H2326 — native firstsend settlement and control polling

H2323 source 6fa10d75e3b7f23f909252e2737948911d3eb64c, [Action 45308263564](https://github.com/lly8666/wbd-next/actions/runs/45308263564), all six jobs PASS. Same TX8/16KiB NPF, FEC OFF, repair OFF. A/B/A-prime actual receiver goodput 192.036/251.586/160.973 Mbps, Windows process CPU s/GiB 30.1517/20.4012/29.6310, sparse P99 250/204/313ms, 160 echoes each, no late >1s, zero NPF short calls, three owned Stops. Candidate vs mean baseline +42.54% goodput, -31.75% CPU/GiB, P99 below both controls. One triplet, drift exists; not universal speedup or high-line qualification. H2323 restored main H2214 manifest patch; prior governance 45308263620 failed solely missing feature-impact declaration. No TLS policy change.

H2326 reduces existing native fixed costs: BTreeMap occupied-entry validation/removal retains invalid pending and avoids second lookup; repair OFF avoids unused per-copied-packet clock; one owner guard polls feedback then repair (only if no feedback), releases before syscall as before. No new queue/worker, no change to repair admission, Health/Auto, AEAD or NPF outcome. New native test checks Accepted/NotSent/Uncertain, malformed/repeated receipts, OFF shadow and Stop; cheap H2311 now executes full Windows owner module, not only one selected regression. Performance of H2326 NOT_RUN; compare separately against measured H2323.

```feature-impact
{"kind":"none","ids":[],"reason":"H2323 restores existing main Windows CLI manifest declaration without altering TLS behavior; H2326 internal native TX settlement and owner polling reduction preserves existing feature semantics."}
```
