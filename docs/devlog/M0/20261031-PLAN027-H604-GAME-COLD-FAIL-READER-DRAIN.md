# PLAN027 H604 — cold Game failure cleanup can outlive the original test

Recovered main SOURCE `8a9a34549835470b1d0d24566d45199bf13b2d35`, M0 cursor603, registry and PLAN027. H603 cheap workflow [41187869573](https://github.com/lly8666/wbd-next/actions/runs/41187869573) passed; the only original H601 Game2 native job [41186157073](https://github.com/lly8666/wbd-next/actions/runs/41186157073) remains CANCELLED after independently scoped recovery 41187706865, not a business/Stop PASS. No duplicate in-flight action at recovery.

User's excerpt shows 200 captured real TCP443 frames (PSH/ACK both ways and an ACK), then `WL_WSL2_OUTER_WATCHDOG_DISARMED` and the workflow's explicit native E2E nonzero throw. This proves neither Go TLS readiness nor driver delivery. The original client/server/direct mode error is needed to attribute the initial product failure; do not confuse the passive witness with a deadlock stack.

Code review found a concrete abort-lifetime error: in `runM0NativeV4WindowsGame`, early TCP/TLS/Apply failures run defer that called `NpcapEndpoint.Close` then `readers.Wait` without ever closing `handoff`; `ReadSegmentUntil` retries every pcap zero timeout until that signal or the gate closes. On failed start, endpoint gate/reader join can retain the Go process and original child long after the actual failure. Minimal fix: one `sync.OnceFunc` close shared with successful `m0WinRustGamePeer.BindNativeRing`, and abort order **close signal → readers join → endpoint Close → associations Close**. A successful move remains single owner; never calls pcap_breakloop or steals Rust capture. No new Go hot loop, packet timing or packet format. Existing H602/H603 360/440/510/600/720s external safeguards stay. This removes a real possible leak but is not proof it caused the supplied run.

New source must compile on Windows and pass exact original Game2 plus Game2/4 FEC, Health/Stop/rotation. Preserve any FAIL and report. PLAN027 §0 A/B/C/long test still OPEN; no physical PASS claim, A5 remains retired.

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Game failed cold TLS/Apply now signals all cold NPF readers and joins before closing driver; successful Rust capture handoff retains single-owned once-close. No wire/protocol change."}
```
