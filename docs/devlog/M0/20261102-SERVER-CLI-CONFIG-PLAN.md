# Server CLI/config follow-up plan, not implementation

User 2026-11-02 requests server-owned borrowed-site domain plus one `wbd-next` console entry for persistent installation, complete uninstall, configuration, client inventory and service start/stop/restart.

Added `docs/decisions/M0-SERVER-CLI-SIMPLIFICATION-20261102.md` and a PLANNED-only feature card (empty available_on/code_refs). Minimal config: listen, server-name, account list. Explicit before-TLS domain synchronization, per-client independent effective settings, automatic identity/address/material responsibilities; no claim existing V4 parser already supports this schema. Reuse old fixed-source deploy/linux/wbdctl and systemd template/lease logic, omit online upgrade/rollback platform.

Defined menu/subcommands, fixed owned install paths, source-matched package, local on-demand client snapshots, config validation+explicit restart, and Stop/owned-network recovery before destructive uninstall. Shared system journal is not wiped. Tests are real systemd/package and per-client semantics, with process reboot vs host reboot and arm64 build vs native execution qualified separately. CLI is cold, no added data-plane periodic report/monitor.

This is planning only: product/workflow/cursor/registry/current PLAN027 task and in-flight runs untouched. Follow-up is discoverable through migration/startup entry and existing feature catalog, not a second governance system. Local checks cover documentation/catalog structure only; product tests NOT_RUN.

```feature-impact
{"kind":"updated","ids":["server-management-cli"],"reason":"Pre-register user-requested server management as PLANNED only; no product implementation, default or test qualification changed."}
```
