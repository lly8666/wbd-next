# H986 PLAN027A — exact SOURCE build once, three independent native scenes

main reviewed at `038136b5e9021c33af600f4069dd06a363e72f9b` (H985); governance registry M0 still PLAN027A, 027 H920 scope accepted. No queued/in-progress Actions before H986. H962 and Fixed FEC2 numeric MSS/record/TUN/Stop were already proved by H981/H982/H984; no repeat of those five Windows or five Linux real cases. Old H978 Fixed1333 and H983 original Go test FAIL remain unchanged.

H958 DF0/DF1 native and H957 staged Game had NOT_RUN. Their old static SOURCE `54160ac8` cannot be reused after new Go product source changes. This batch adds one source-gated GitHub Actions orchestration triggered by its own workflow path: run original Windows signed Wintun/Npcap + WSL2 Linux original Go/Rust Normal/default1460 as ONE exact-source build, check both artifact names, then dispatch precisely three separate actions for DF0 1728B + DF1 local EMSGSIZE (5Mbps 0% 60s), Auto FEC2 5Mbps 250ms staged 5/30/5, Game4FEC 3Mbps 250ms staged 5/30/5 (210s stages 0/40/80, final 130s observation). Single run per independent scene, no new GO formula, packet protocol, LINK capability, 1500 default, per-scenario product rebuild, or invented PASS.

H986 action is a dispatch/build gate, **not itself a performance result**. Artifact `docs/evidence/M0/PLAN027A-H986-SOURCE-BUILD-THREE-SCENES-20261103.json` intentionally records NOT_RUN until source-verified real receipts are collected. DF1 local EMSGSIZE does **not** prove a native ICMP Type3/Code4 was generated; that remains NOT_MEASURED. Existing Rust shared RFC791 fragmentation/ICMP codec and Linux Game integration are not rewritten. Remaining PLAN027A gates and PLAN028 sequencing remain open; physical WAN unknown.

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Added source-gated native DF and staged Auto/GameFEC qualification fixtures with initial NOT_RUN; no product behavior/default claim."}
```
