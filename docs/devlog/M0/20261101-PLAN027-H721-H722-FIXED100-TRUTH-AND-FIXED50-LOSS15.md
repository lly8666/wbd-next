# PLAN027 H721–H722 — Fixed C100 negative business, true Stop, and one damaged Fixed next

Current R0-M0-PLAN027-FEEDBACK-AND-NETWORK-CLOSEOUT stays PARTIAL, physical NOT_RUN.

Source d0661a2e110b523ad06b311da23fc1b7291442ba original signed Windows NPF/Wintun↔WSL2 Linux Go credential TLS/Rust binary build 41274450306, manifest-verified ZIPs windows13071196733 sha256:b6baac6ba45a6825665addf329447e56564240c310ae8f636d119b6c6d0eaa6a / Linux13070622152 sha256:837cb7a113f871914c2d04f0caead8a93a7a97ce7e3bd53c9878819cd9dbb5c3. H718 Fixed6 C50 run41276271649 real first100% both, owned Stop PASS.

H720 C100 one Action [41276671847](https://github.com/lly8666/wbd-next/actions/runs/41276671847) source/controller 1b3a4ae3, original binaries d0661a2e110b523ad06b311da23fc1b7291442ba, native job124760189731 **FAIL**. Real 60s/25ms/0% each: offered 99.9733/99.1814Mbps, first delivered 98.9329/98.0952Mbps, first unique Windows99.7456%, Linux98.1900% BELOW 99.9 threshold, true Linux TUN TX drop2503, WSL generator CPU54.1391s, NPF local drop0. Both real UDP/TCP initial and actual Rust owner Stop readback + server exit PASS, not overall performance PASS. Distinguish apparent `WL_REAL_LINUX_OWNED_STOP_REQUEST_FAILED code=1` after successful Stop: existing Python finally sent second SIGTERM to already exited PID; H721 harness commit972c71 suppresses only redundant second attempt, retains first/real stop assertion. No product CPU/transport gain claimed. Full real report artifact13071399351 sha256:ea911147548e5b90f195e3ebc497118fe7abef86bdb5ba3497b2f028b02d4f69. Independent watcher41276679368 **PASS log salvage** via RUN_VIEW, not native PASS.

Do not step to higher Fixed zero-loss offered family after C100 host/product drops. Continue different capacity-valid C family: H722 exactly one highest Fixed50Mbps/250ms/15% actual kernel native scenario `scenarios/plan027-c-fixed-50m-250ms-loss15-60s.json`, immutable binary reuse; controller authenticates original source/manifest and H718 clean C50, allows only H721 no-second-kill harness delta, independent watcher automatically arms in existing native workflow. Controller dispatch green does not qualify product.

B Game2FEC1M SOURCEd066 run41274450306 and Windows blackhole106 run41275015266 **CANCELLED external** with 404 BlobNotFound; preserve first error and Stop UNKNOWN. Do not call their binary compile proof a network PASS, do not repeat identical cancelled scenario. Further B lifecycle/rotation/FIN-DORMANT/host global DNS/WFP/IPv6/config, bilateral F/R/C and final C remain. No legacy A5 rerun (WAIVED_BY_USER).

```feature-impact
{"kind":"updated","ids":["fec-fixed"],"reason":"H720 genuine Fixed6 100Mbps zero-loss source d066 FAIL first delivery and Linux TUN drops despite original owned Stop PASS; H721 harness only avoids duplicate second signal; H722 one different 50Mbps15pct C native request, not qualified until result."}
```
