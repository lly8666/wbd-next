# PLAN027 H819 | Parallel N-line real-loss repair-OFF control from R frozen binary

- H817 R Action `41342800664` SOURCE `f5e8f30fa4a5052c9797bbd15b385ec5cfc5d2c3`: exact Linux original-Go+Rust x86_64 product artifact `plan027-r-once-frozen-linux-product` uploaded and source/hash manifest verified. Native OFF→ON paired CPU job independently running, result **NOT_RUN/pending**.
- N asks whether a 30% damaged network remains authentically productive with **outer DATA repair disabled**, without confusing FEC/driver capacity or ON presentation repair. One original existing scene `wl-outer-repair-10m-250ms-loss30-60s.json`, each way 10 Mbps payload/250ms latency/30% true tc/60s, unchanged 64/128/512/1200B distribution; UDP-only (no user TCP p99 claim). Expected no-repair first arrivals near the applied loss ratio (~70%) before host/queue drops; measure, do not hard-code a narrow recovery floor.
- New one-scenario `m0-plan027-linux-normal-off30-reuse.yml` Action uses SAME H817 binary artifact, manifest SHA and original `SHA256SUMS`; additionally checks `git diff --quiet PRODUCT_SOURCE..FIXTURE_SHA` for product code/assembly paths. Actual product source **f5e8**, current fixture source new H819 commit, explicitly separate. One native Linux original Go TLS client+server Rust raw/TUN in owned namespaces, OFF readback, F/R=0/C not measured, actual tc drops, first-delivery, CPU/RSS, both owned Stop. Independent Action can run while R paired measurement is in progress; no binary rebuild, no Windows result.
- H818 current cursor reference bound 8: governance Action `41342911798` PASS. No product optimization yet; neither N nor R result can claim FEC/Game or ON integrated PASS.

```feature-impact
{"kind":"none","ids":[],"reason":"N-line source-frozen measurement tool/workflow reuse only, no product code/config/defaults or feature status changed."}
```
