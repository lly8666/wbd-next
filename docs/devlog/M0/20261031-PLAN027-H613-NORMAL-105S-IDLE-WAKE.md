# PLAN027 H613 — B lifecycle real payload idle >90s and first-new wake

User explicitly requested parallel independent work rather than a Game-FEC serial blocker. H610 A2/A3/C separate Actions already running; H612 Game2-FEC isolated. Add one *Normal/off* genuine TLS/NPF/Wintun↔Linux raw/TUN test: after source-authenticated real bilateral UDP+TCP and both sockets terminate, maintain **105 seconds without application payload** and observe neither true product owner exit. Then launch fresh original socket fixtures on Windows and WSL to require >=24 real sends and >=12 new received packets **in each direction**, followed by the existing same-SOURCE 10Mbps/25ms/0%/60s V2 kernel load and both owned Stop. This tests that authentic Health avoids false >90s dead and business can wake; it does **not** demonstrate a 90s blackhole or lane rotation, nor claim explicit Health packet count. The original product binary is exactly SOURCE `80ee526cc7b466ec6ccbe3cc25caf2f3754996ef` from build run `41190352345`; only test fixture/parser/scenario changes, one standalone Action, no new production timers, old Go data plane or repeated build.

Work remaining: Game2/4FEC actual Stop, actual 90s blackhole/dead, rotation, DNS/IPv6/MTU, Auto quality maturity, C capacity limits and 300s long verdict. No interim PASS extrapolated.

```feature-impact
{"kind":"none","ids":[],"reason":"Independent source-locked original Normal B 105s idle/wake test fixture only; production behavior untouched."}
```
