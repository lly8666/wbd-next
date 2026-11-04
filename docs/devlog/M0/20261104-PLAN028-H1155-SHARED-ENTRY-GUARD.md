# PLAN028 H1155 — shared one443 server admission entry only

Collected [H1154 Action41848636350](https://github.com/lly8666/wbd-next/actions/runs/41848636350), artifact13334415224 sha256:6559e9bbe4719fe67ffaa9ab9f79fe1e18acde8d3ea6a7ac49b180c409339ec6. Exact SOURCE6e4337 builds original Go TLS/Rust ELF62, mixed V3 protected Game2/Game4/Normal Go tests all PASS. The genuine native stage failed before AF_PACKET startup: server log `realityfront: V3 policy unsupported by this build`. Narrow code cause: `Run` calls `runGame` for server `--mode shared`, but `runGame` begins with old standalone `c.gameLanes!=2&&!=4` rejection. Shared server deliberately keeps process-wide lanes=0 and existing `runGameServer` delegates to `runGameMultiServer` when the server has its verified lease pool.

Fix only opt-in mixed server guard in `r0/go_overlay/internal/v4productcli/game_linux.go`: allow `c.role=server && c.mixedModes && c.gameLanes=0 && c.leasePool.IsValid`; preserve old dedicated Game2/4 checks. No change to protected original TLS, Game cohorts, FEC/AEAD/PN, shared TUN demux, network MTU or packet wire. Add this source file to the existing one-scene workflow path triggers so one complete new compiled SOURCE can be verified; do not dispatch helpers. H1154 is NOT a 48-UDP PASS, and historical H998 shrink FAIL, older ARM Game Action FAIL, remote ICMP/Android/CPU limits remain.

```feature-impact
{"kind":"none","ids":[],"reason":"Cold Go shared-server mode entry selects already existing authenticated mixed Game/Normal server on one443; no product wire or FEC algorithm changed; native pending."}
```
