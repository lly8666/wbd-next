# PLAN028 network-change recovery scope

User requests client-initiated reconnect after switching networks, with server reauthentication, and confirms the new default outer IP MTU is 1460. Reviewed main at cd3f2e8b: the MTU contract, PLAN027A/028/029/030 and prompts already use default1460 / explicit maximum1500. Preserve that change and the earlier dated evidence; do not rewrite historical1500 defaults or change product MTU code.

Decision: implement common session continuation/path-change handling and native Windows/Linux client notifications in PLAN028; Android-specific network callback, underlay socket binding/VPN bypass and physical Wi-Fi/cellular qualification belong to the later Android client work. Do not defer the shared design to Android or block desktop delivery on Android.

Updated PLAN028, its startup prompt and rollout entry. Specify coalesced event-driven cold reconnect, reuse of the existing controller/TLS/authentication, authenticated device/session+lease continuity, same-account device isolation, owned lane/generation handover, raw/Npcap rebind, automatic path MTU and Auto-FEC reset, dormant/explicit Stop behavior, stale completion/resource cleanup and bounded retries. No new steady-state packets, per-packet ABI, public MTU setting, second lifecycle controller or new migration wire protocol. Reuse seven-mode rotation fixtures with a real path switch; add only representative Linux-client notifications and break-before-make/MTU/debounce cases. Report each recovery phase and CPU/p99; 500ms is notification handling budget, not a high-RTT authentication SLA. Android/physical remain NOT_RUN.

Existing lifecycle and authentication feature cards gain PLANNED notes only; no source qualification promotion. Current PLAN027A registry/cursor, product code and running Actions remain untouched. Removed the rollout/prompt's stale instruction to restart PLAN027 for historical NOT_RUN after its user-authorized scoped closeout.

Validation scope: documentation references, feature-impact/catalog consistency, governance structure and whitespace. No product tests dispatched for this documentation update. Runtime/platform behavior is planned and must be implemented/qualified by the PLAN028 owner.

```feature-impact
{"kind":"updated","ids":["idle-rotation-keepalive","tls-auth-multiclient"],"reason":"PLAN028 now specifies common authenticated network-change/session continuation and Windows/Linux event wiring, with Android adapter/testing deferred; plan-only notes, no runtime or verification promotion."}
```
