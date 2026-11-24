# M0 H2414 mixed Normal/Game shared /32 handoff

User report: disconnect Normal -> Game2/4 connected but reverse injection zero until reconnect after Health90. Rust defers replacement by /32, but Go only checked the same transport table. Fix cold lookup and retirement over both existing active and pending maps, using authenticated lease rather than mode, principal alone or tuple. Preserve immediate initial publish, existing Health proof, exact generation retirement, grace and 90s. Align Game exact-already-published promotion result with Normal when old A disappears before B start. No new wire, FFI exports, states, worker, timer, packet-path change. Game4 selected-slot hot replacement unchanged. Manifest hash regenerated. Tests NOT_RUN until exact SOURCE.

```feature-impact
{"kind":"updated","ids":["game-lanes","linux-raw-tun"],"reason":"Correct cross-mode cold shared-TUN owner publication and retire only predecessors of the same authenticated /32; no new user option or protocol."}
```

Exact native dual-ISA fixture: persistent installation ID, same one443 shared server, reverse-first TCP/UDP each whole-owner switch, same-account separate auto lease, Game4 hot selected-lane, original Health90 and exact joined Stop. Deliver only after real Linux receipt; same SOURCE Windows GUI via existing H2216 complete package job (GUI/owner self tests, physical Windows mixed switch NOT_RUN). No product tests have run yet.

First test Action45426955665 Linux jobs failed before checkout: setup-go pin could not resolve. Use GitHub verified v5 commit 40f1582b2485089dde7abd97c1529aa768e1baff. Feature catalog exceeded 16KiB UTF-8 bound after new entries; compact JSON without changing fields. Product results still NOT_RUN.

Fixture correction from reading V4EpochStore.prepare: existing old+new per-lane overlap cap must not be exercised as a third-incarnation switch. Dwell with the NEW owner live until previous existing grace retirement, prove post-Stop business; next disconnect -> connect still immediate. Final Game4 selected-lane interval 25s leaves ordinary old-owner grace intact. No product change from c04b46d; first active run remains evidence and is not canceled.

ARM64 and x86 quick Action45427122913: initial Normal and immediate Normal->Game2 and Game2->Normal real reverse/forward TCP/UDP PASS and sibling lease PASS; rapid subsequent Game4 fixture failed protected_epoch_reserve until previous grace, not a route-promotion failure. ARM artifact14936917111 independently read exact native deferred/promotion and retire logs. While checking reported Windows path, found second real mismatch: Windows Game tx_loop created HealthClock without existing arm_client_cold_ready (first steady 15s), server's existing successor proof 5s. Normal Windows already arms it. Initialize the actual Game TX clock with the same existing cold Health function and start RX before TX using existing worker handles; no new state, timer, wire, steady polling or driver change. Unit exercises the exact initializer, 4..7 copies in <=3.5s and unchanged 15s/90s. Windows real peer switch NOT_RUN until native evidence.

```feature-impact
{"kind":"updated","ids":["game-lanes","windows-native-transport"],"reason":"Complete existing Windows Game cold Health proof wiring to make mixed-mode server owner handoff work with real Windows client, unchanged steady Health and lane lifecycle."}
```


Add an independent signed Windows2025 Npcap/Wintun → WSL2 real peer fixture using the exact already-running a4c5c975 product artifacts, no duplicate build. Same authenticated manual lease, one server, Normal/Game2/Normal/Game4/Normal, reverse TCP/UDP first, existing grace then next cold switch. Physical deployment remains out of scope.


Windows pair Action45429168582 initial fixture failed before first Normal TLS: repeated SYN, server no auth, same known WSL MAC/SendARP fixture omission as original public native workflow. Actual failure artifact14939450781. Reuse existing exact WSL neighbor binding and verified MAC/IP/ifindex FFI test handoff, no product rebuild/change. Windows binary a4c5c975 owner 91/91 and explicit cold Health initializer 1/1, GUI 433/433. Linux same SOURCE both native jobs PASS. Retest exact existing packaged bytes.

Windows pair Action45430196116 initial Normal real Npcap TLS/M4/Wintun OS_APPLIED and joined Stop PASS. Test application before switching failed Windows TCP bind 47001 WinError10013 (artifact14938322452). Choose actual bindable application-only TCP+UDP ports in fixture; preserve one configured 41031 and allow the original persisted ordinal's bounded consecutive test tuples rather than wrong per-mode fixed port windows. No product change; same exact three packages.


H2416 PASS exact product a4c5c97591e9b9ed6fa16221e6666c531d1909cc. Action45428320586 all three jobs PASS; Linux dual ISA each 8 immediate same /32 cross-mode promotions, 96 real direction TCP/UDP probes, sibling lease, old grace, Game4 hot lane, Health90 and Stop. Signed Windows actual packaged pair Action45430747305 PASS: Normal/Game2/Normal/Game4/Normal, 4 unique promotions, 4.687–6.688s reconnect to duplex, after-grace business, owned Stop; downloaded receipt and all package checksums independently verified. Existing overlap cap preserved. No physical WAN/old kernel retest/performance A/B claim. Evidence: docs/evidence/M0/20261124-H2416-MIXED-MODE-ROUTE-HANDOFF-PASS.json
