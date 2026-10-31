# PLAN027 H647 — force native result before outer watchdog, not after

Real original GameFEC 15% SOURCE11f Game2/4 Actions41211105194/41211110192 and Normal/Fixed B106 41211114737/41211119313 were external-CANCELLED with native BlobNotFound. Audit of code shows Game mode360/batch440 + uncounted preflight/cleanup exceeds Windows step600; other V2 mode1200/batch970 + preflight/cleanup exceeds Windows step1020. Hence the external720/1200 cancel may erase the original failing job *before the nested bounded mode can report*, independent of whether the Rust product itself blocks.

One scene only: mode Game240/batch310/whole-step600/external720; Normal/Fixed V2 mode690/batch760/whole-step1020/external1200. Margin includes original Windows WSL2/Firewall cold OS and owned Stop; do not extend watchdog, remove real driver or invent green. Original 60-300s application scenes remain inside. No new Go hot actor or FEC/control wire.

B106 test must see **Windows** WBD_WINDOWS_NATIVE_DEAD_RECONNECT_ARMED and WBD_WINDOWS_ORIGINAL_GO_TLS_REAUTHORIZE plus second authentic CLIENT_READY, as well as existing **Linux** original TLS reauthorization and actual bilateral kernel UDP/TCP/owned Stop. Previous single-Linux marker could not certify both actual generations.

H646 Game4off30/Normal50loss15/Fixed50loss15 already independent Actions IN_FLIGHT, no repeat. Same SOURCE11f binaries from Action41210457594 can be used for one Game2FEC15 and one NormalB106 on new test harness only after cheap CI tests. All remain NOT_PASS until original native artifacts.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct only V2 original Actions nested timeout precedence and B106 true dual TLS-generation evidence; production Rust/Go protocol, owned Stop and config unchanged."}
```
