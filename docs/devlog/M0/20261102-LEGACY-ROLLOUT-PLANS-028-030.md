# PLAN028–030 planning only; existing PLAN027 work preserved

User requests a future legacy-feature rollout, split for fresh-agent context, explicit parallel work and per-package M0 prompts. Initially reviewed main at 59f00500/H867 and fixed legacy oracle a7a82db31fe736ffedee330795a3234d358f1984; refreshed through 0d6ba006/H870 before publishing. No product changes or Actions dispatch; existing M0 assignment/cursor and in-flight qualification unchanged.

Added one short index and three implementation packages: 028 auth inputs/leases/single-port multi-client/per-session effective config, 029 server-domain bootstrap DNS under Windows capture/UI/bounded new-flow padding, 030 thin server CLI/systemd/package/owned uninstall. Each has a reusable prompt. Freeze minimal shared contracts first; independent modules and distinct Actions can proceed concurrently, shared ABI/WAL/auth edits remain serial. Build once/reuse exact SOURCE+hash; no repeated full PLAN027 matrix.

Index records scoped Linux Normal300s/Game4 passes, missing actual rotation evidence, Windows OFF/rotation open items. Pre-publish refresh incorporated H870 exact b747 single/both-direction recovery scoped PASS while retaining source377 failure and unresolved b747 negative observation; Windows receiver changes are not yet qualified. No promotion to Windows/physical PASS. Mature Health 15s/dead90s/backoff1–30s/lease7days and existing fixed-cipher/generation/MTU/owned semantics preserved. Seven mode actual A→A+B→B rotation is explicit; high-loss retry/residuals allowed. Defaults are not silently replaced with the user's earlier trial preset.

Domain design separates dial address from borrowed SNI, binds bootstrap DNS to physical egress with narrow owned capture exemptions through reconnect/wake/rotation, and preserves user DNS policy. Padding is opt-in, bounded and never delays fresh business; no new protocol probe or periodic flow restart. CLI uses existing cold control, no extra steady daemon or upgrade platform.

Deleted standalone M0-SERVER-CLI-SIMPLIFICATION-20261102.md from active plans, replaced links/card with PLAN030; original devlog and immutable historical link preserved. Root completion rule now follows the active plan; current PLAN027 remains explicit. Follow-up cards stay PLANNED with no available/code/PASS claims. Static governance/catalog/link checks only; product tests NOT_RUN because this change contains plans, prompts and feature records only.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","dns-split-ipv6","gui-config-feedback","server-management-cli","client-domain-bootstrap","startup-flow-padding"],"reason":"Plan-only legacy rollout 028–030 and scoped feature registration; no product implementation or qualification promotion; standalone CLI proposal replaced."}
```
