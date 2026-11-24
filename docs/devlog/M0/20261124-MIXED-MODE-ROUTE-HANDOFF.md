# M0 H2414 mixed Normal/Game shared /32 handoff

User report: disconnect Normal -> Game2/4 connected but reverse injection zero until reconnect after Health90. Rust defers replacement by /32, but Go only checked the same transport table. Fix cold lookup and retirement over both existing active and pending maps, using authenticated lease rather than mode, principal alone or tuple. Preserve immediate initial publish, existing Health proof, exact generation retirement, grace and 90s. Align Game exact-already-published promotion result with Normal when old A disappears before B start. No new wire, FFI exports, states, worker, timer, packet-path change. Game4 selected-slot hot replacement unchanged. Manifest hash regenerated. Tests NOT_RUN until exact SOURCE.

```feature-impact
{"kind":"updated","ids":["game-lanes","linux-raw-tun"],"reason":"Correct cross-mode cold shared-TUN owner publication and retire only predecessors of the same authenticated /32; no new user option or protocol."}
```

Exact native dual-ISA fixture: persistent installation ID, same one443 shared server, reverse-first TCP/UDP each whole-owner switch, same-account separate auto lease, Game4 hot selected-lane, original Health90 and exact joined Stop. Deliver only after real Linux receipt; same SOURCE Windows GUI via existing H2216 complete package job (GUI/owner self tests, physical Windows mixed switch NOT_RUN). No product tests have run yet.

First test Action45426955665 Linux jobs failed before checkout: setup-go pin could not resolve. Use GitHub verified v5 commit 40f1582b2485089dde7abd97c1529aa768e1baff. Feature catalog exceeded 16KiB UTF-8 bound after new entries; compact JSON without changing fields. Product results still NOT_RUN.
