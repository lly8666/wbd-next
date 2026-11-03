# H992 — finish 11 native results and retry exactly two failures

H990 binary source 1e8325f16e2975a9da3497ab97ac570771a97238, fixture b03332b9886ed2321b8711b149bc8e78325b797d. Dispatcher 41554842970 PASS, all eleven child Actions completed: NINE PASS and TWO FAIL. Original failures are preserved in docs/evidence/M0/PLAN027A-H992-H990-11-NATIVE-COLLECT-20261103.json.

Passing native modes: Fixed1460 41554882448, Game21460 41554892070, Game41460 41554905507, Game2FEC1460 41554912671, Game4FEC1280 41554928445, Fixed1500 41554935893, Game4FEC1500 41554944208, Auto revision2 41554953134, Auto adaptive 41554960288. They had true original Go TLS, Rust owner, Win32/Wintun and WSL2 TUN, intended source, and native Stop; do not rerun or extrapolate.

Failure 41554919787 Normal outer1280 occurred before business readiness: Python source-locked MSS validator rejected configured outer1280 as forbidden by its OLD (1400,1460,1500) test-only tuple. Native 1280 was already supported in normal cold Rust contract. H992 adds 1280 to verifier with independent SYN/SYNACK 1240 / TUN1209 vector and mismatch negative guard.

Failure 41554874742 H990 new extended Normal DF was observed after real both OS outer1460 inner1389 readback and original UDP/TCP smoke, but Windows socket reported no matching complete UDP 1728/4096/65507 datagrams and stage TCP timed out; NOT a PASS, even though prior H987 one-size 1728 independent Action 41548218023 PASS. New H992 code synchronizes each separate native OS datagram size before sending, inserts TCP stage barrier after the real socket LISTEN, logs sanitized unexpected input diagnostics, and includes both per-side df logs in Actions artifacts. This protects against different-size receive timing but does not waive any original exact-byte requirement. No security/ciphertext workaround.

H992 dedicated workflow dispatches only these two failed original native scopes, reuses same source-locked true binaries and checks no product Go/Rust diffs. No new original Windows/Linux product build. H992 commit carries [plan026-coding] only to suppress normal main push expensive automatic product rebuild, not to indicate any PLAN026 pass.

Remaining independent gaps (NOT_RUN): in-place dynamic route/physical PMTU 1460→1280→1460; actual ICMP Type3 Code4 remote native observation (DF1 local OS EMSGSIZE is not ICMP); current source-specific ARM64 GameFEC; same-VM performance A/B and physical WAN. Do not call PLAN027A complete or start PLAN028 while gates unqualified.

feature-impact: path-mtu-budget receives real H990 scenario evidence but product behavior is unchanged.
