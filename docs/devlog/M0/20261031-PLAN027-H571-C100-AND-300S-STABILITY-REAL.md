# PLAN027 H571 — source525 C100 and 5-minute original kernel stability measured

Original binary SOURCE `52566af216edf9dee4068f0bb8bfd0fb8d18dfcb` reused Windows artifact13028693506 SHA881c64d6de8ebbfa98eda77022e011e4ac18458f783a38913186dbda3da8a291 / Linux13028673203 SHA0d5eb97b89b5d071b4e39ef282debc936cd6fcbf95acbc6d2668ea7ad298cd41, no recompile.

- [C100 Action41170803766](https://github.com/lly8666/wbd-next/actions/runs/41170803766) original both OS Normal/off 100M each/25ms/0%/60s: offered99.9749/99.9997Mbps, first99.9992/100%, actual windows F862417082/R0/C322092, linux F848673931/R0/C NOT_MEASURED, real UDP/TCP/owned Stop PASS, NPF drop0; full Windows Go+Rust process CPU44.2188s in77.203s (~57.3% of one core), peak RSS43.1MB. True 100% lossless on Windows not asserted (8ppm first missing). Artifact13031017688 sha0ab15cfd1d965189db4ae473fded6a410fffb06c4977d703f2eb578d7a2cb94e.
- [Stable 300s Action41170805473](https://github.com/lly8666/wbd-next/actions/runs/41170805473) original Normal/off 50M each/25ms/0%: offered49.9973/50.0000Mbps, first100% both, Windows F2156892088/R0/C4466544, Linux F2122019385/R0/C NOT_MEASURED, true dual UDP/TCP/owned Stop PASS, Windows total CPU38.0312s/317.812s (11.967% one logical core), peak RSS42.1MB. Artifact13031341892 sha49c971e0eead4e605c55d3cebb3000e2e17d668b5d7124e0cf514fbb3f104897.
- Guarded exact C100 genuine report gate [41171215690](https://github.com/lly8666/wbd-next/actions/runs/41171215690) completed SUCCESS and dispatched **only** C200 Action [41171236689](https://github.com/lly8666/wbd-next/actions/runs/41171236689), Normal/off 200M each/25ms/0%/60s, original same SOURCE525, IN_PROGRESS. If host/plugin bottleneck at200, report measured capacity and stop higher same family; no projected PASS.
- The two Game highestFEC B runs41170807537/41170809210 were independently launched with new external actions-cancel watchdog, native results still IN_PROGRESS at this log checkpoint; do not redispatch or treat previous cancelled jobs as PASS.
- Main Governance check41171016585 after corrected SOURCE evidence schema PASS, and checks for later commits also ran. The new Linux-hosted watchdog has been seen disarming on successful native C100/C50-300s run, but **real hung-host cancellation has yet to be proven**.

This is genuine scoped source measurement, not 200M, Windows B lifecycle, A5 old Go CPU, physical or calibrated one-way p99 proof. Detailed JSON [H570](../evidence/M0/PLAN027-H570-SOURCE525-REAL-C100-AND-C200-INFLIGHT-20261031.json), and [H566](../evidence/M0/PLAN027-H566-SOURCE525-RECOVERED-TWELVE-SCENES-20261031.json).

```feature-impact
{"kind":"updated","ids":["windows-native-transport","linux-raw-tun","normal-off"],"reason":"Scoped new SOURCE525 true original C100 and 300-second Normal/off first-delivery, F/R/C, CPU/RSS/Stop evidence; no production code or config change."}
```
