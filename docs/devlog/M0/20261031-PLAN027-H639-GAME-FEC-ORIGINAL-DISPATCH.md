# PLAN027 H639 — launch original Game FEC 15% and Game outer 30% real Windows/Linux

The H637 exact source Windows Rust eligible library test, Linux Rust eligible test, Windows Go production build, Feature catalog and Governance all completed SUCCESS. These are compilation/library gates, not original wire evidence.

The source-locked dispatch gate introduced in H638 used `test -f` before checkout; H639 moves checkout before the opt-in dispatch to validate three committed source scenarios safely. This commit deliberately includes `[m0-real-game-fec]` to trigger the workflow once. On push, the dispatcher checks that the protected live `main` ref is still this exact commit SHA, then requests three **separate** `workflow_dispatch` Actions: Game2 fixed6 FEC loss15%/75ms/20s, Game4 fixed6 FEC loss15%/75ms/20s, and Game2 FEC-off loss30%/250ms/60s. Original Windows Npcap/Wintun, original Go TLS lanes, Linux peer and owned Stop are mandatory; no synthetic acceptance.

Dispatch launch is not native execution or PASS. Every child has an independent native deadline and produces its own evidence; cancelled, failed or missing artifacts remain explicitly not-PASS. H627 B106 idle death and Auto lossy source qualification remain open.

```feature-impact
{"kind":"updated","ids":["game-fixed-fec"],"reason":"Source-specific three-mode original native Game FEC and Game outer network qualification dispatch, checkout before scenario verification; feature not promoted without actual evidence."}
```
