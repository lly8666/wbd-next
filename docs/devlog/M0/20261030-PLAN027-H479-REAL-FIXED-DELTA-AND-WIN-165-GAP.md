# H479: actual post-fix 3-scenario Windows CPU and residual source losses

Original binaries frozen source a61eef334068512b00a1db3137a51f3d0489020c. New H478 source fixture only, all three real Windows Wintun/Npcap ↔ Linux WSL2/TUN original Go TLS/Rust Action-owned Stop PASS.

- Normal10M0: win Python generator86.731%→6.394% core, loop9.155m→124869, exact 100% first delivery both, Win UDP SO_RCVBUF actual16MiB, global in_errors0.
- Normal100M0: win generator82.212%→16.13% core, windows consecutive missing411→165 IDs (120087..120251), Linux first100%; Win NPF drop0, both Linux tc drops0, Win host-global IPv4 UDP InErrors0. This remains **STRICT ZERO-LOSS FAIL** notwithstanding preexisting legacy >=99.9% first admission or Actions success. The OS MIB is global and 0 cannot prove Wintun or NPF never dropped.
- Fixed10M250ms30%: Windows generator89.375%→5.625% core; Windows residual source loss .3717%→.0121%; Linux .0734%→.0241%; 12 missing Windows and 24 Linux, owned Stop. No new FEC algorithm, product binary changes, or unsupported pure lossless guarantee.

H479 adds standalone first-count exact-zero fail-closed oracle. Next pinpoint 165 Windows source gap at product-before-Wintun vs app-after-Wintun boundary; do NOT mark PLAN027 ready.
