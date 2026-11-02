# PLAN027 H869 | Windows original authenticated retirement RX adapter, unit only

- H867 immutable source b747 original Linux unilateral c2s105 process PASS but bilateral105 process FAIL_OR_INCONCLUSIVE. Both actual result uploads missing from H867 job path mismatch, H868 two isolated same-source receipt collection Actions41385220985/41385221081 in-flight. No new business metrics invented, no re-dispatch to vary seed.
- Shared `parse_authenticated_control` already checks exact retire kind1 under the original M3 AEAD+unique PN gate. Windows native `m2_authenticated_kind1_entry` previously refreshed ordinary Health and **ignored** `control.peer_retire`, leaving a Windows side on its old generation when Linux warns. Correct Windows-specific receiver to call its existing current-generation `HealthClock.on_authenticated_peer_retire(now)` solely on that M3-authenticated control, letting existing Windows TX loop return AUTHENTICATED_PEER_DEAD to Go and use owned Stop/TLS reauthorization. Avoid raw ACK, fake liveness, new control carrier or second timer. Unchanged Windows transmitted notices; complete asymmetric Windows-originated notice still NOT_RUN.
- Unit test establishes actual bound Windows owner/M2 epoch, verifies ordinary authenticated Health does not retire, exact parsed retire makes HealthClock unhealthy, does not mutate Quality, and owned quiesce/Stop/release. Existing Windows-Rust ABI workflow will test same SOURCE; **no claim of native Windows real rejoin or OFF**.
- H864 current baseline source377 original Linux Normal ON300 mixed HOL PASS and Game4/FEC6 ON20M30 PASS scoped only old source; do not rescope to H869.

```feature-impact
{"kind":"updated","ids":["normal-off"],"reason":"Windows original M3 replay-verified authenticated generation retirement receive path now reaches same current HealthClock as Linux; Windows sender/full native test still pending."}
```
