# H750 — Windows native-only unread stdout pipe test, still GameFEC only

H748 source ba8c487 GitHub Actions41289214593 and governance41289214607/41289214648 PASS, including real Linux unread OS stdout pipe + one-shot `faulthandler` and PID deadline=1s. H749 source95d884 one genuine 1Mbps 25ms 0% 10s Windows NPF/Wintun original Go TLS Rust↔WSL2 Linux Game2FEC now **IN_FLIGHT** run41289375904, watcher41289383815 native-step cutoff480s, original product SOURCE0264 frozen binaries from build41280564979. Controller41289361933 SUCCESS dispatch only, no product PASS.

The Linux PIPE fixture is essential but insufficient proof for Windows CreatePipe buffer, Python interpreter teardown and `taskkill.exe /PID /T /F`. This H750 single Windows2025 fixture invokes the SAME `test_h748_actual_unread_os_pipe_full_does_not_hold_game_deadline` and 1s synthetic native owner with a real unread OS PIPE. It allows at most 18s for Windows process spawn + owned taskkill, requires bounded status124, at least Windows pipe 4096 bytes of unread output and original separate faulthandler thread stack. No WSL, Npcap, Rust, credential, network impairment, or new real product run; one test job only. H749 in-flight product remains separate and unchanged.

All unrelated PLAN027 work remains PAUSED by user, overall task PARTIAL.

```feature-impact
{"kind":"none","ids":[],"reason":"GameFEC-only Windows native PID supervisor synthetic unread pipe fixture, no product code modification."}
```
