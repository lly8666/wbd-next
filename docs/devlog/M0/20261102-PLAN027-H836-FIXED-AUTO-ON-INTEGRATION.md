# PLAN027 H836 | Independent Fixed6 and Auto outer ON adapters, product SOURCE frozen

- Existing original Linux source-frozen source f5 at Normal/Fixed6/Auto/Game2/4 N OFF, Normal ON A/B/300s, Game4 ON and Auto natural 240s all scoped with actual independent network evidence. PLAN027 affected Fixed6/Auto ON combinations remain missing, not covered by OFF success.
- Two **independent Actions**, one scenario per Action/one measurement job each, reuse EXACT `plan027-c-game2-fec-10m-250ms-loss30-60s.json` and SOURCE `f5e8f30fa4a5052c9797bbd15b385ec5cfc5d2c3` original Go TLS/Rust M4 product artifact from run41342800664. Same 96/288/1060/1200B packet mix (avg910.8B,10Mbps ~1372 business pps/dir, 500ms RTT BDP625kB payload/dir) as previously measured Fixed6/Auto OFF. Only set `repair_enabled=true`, preserve mode/actual FEC profile/OS, verify native readback, actual parity, R/F<=10% per direction where M4 ledger exists, real 30% tc drops, first unique delivery≥99%, CPU/RSS, owned Stop/netns clean. No new binaries or user-facing options.
- This is an ON functional integration, **not** same-VM causal CPU pairing to previous OFF Actions (independent runner/real loss samples differ). Both use shared Go/Rust original Normal single-lane repair producer; no cosmetic separate clone or new controller. Do not force positive R merely to prove work—FEC may fully cover observed gaps.
- H835 blackhole105/restore120 original Linux source-frozen Action `41351767832` still running; H833 Windows signed Normal native Action `41351342840` in Windows Rust DLL/NPF setup; retain and collect before any duplicate.
- Missing Health-loss/rotation/Windows OFF pairing, F/R/C complete Game four lanes, potentially R throughput/lock-stack profile and physical gate remain open; no product optimization without measured attribution. Two ON scene results still **NOT_RUN/pending** here.

```feature-impact
{"kind":"none","ids":[],"reason":"Two source-frozen original single-lane FEC ON measurement Actions and one narrow input fixture with shared real policy; no product, config help or feature default changed."}
```
