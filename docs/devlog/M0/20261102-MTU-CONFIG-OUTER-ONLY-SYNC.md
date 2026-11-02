# Follow-up plans: user MTU always means outer IP ceiling

User confirms ordinary MTU configuration remains the complete outer IP packet ceiling (default1500, excluding Ethernet) and requests downstream plans remove ambiguity. Synced the sole MTU contract, PLAN027A and 028/029/030, their four startup prompts and the rollout index.

Inner TUN/Wintun MTU is derived/applied/read back automatically, displayed read-only. Removed the contract's ordinary advanced inner override wording; explicitly labeled test/experiment compatibility overrides remain separate. Saving1500 must preserve user intent even when effective outer/inner is lower. Client per-session intent is constrained by actual server/local path limits, never copied blindly to the shared TUN or made a second mandatory server field. GUI/server snapshots use explicit outer/effective/inner labels; padding consumes the same budget. Added ordinary fixture and save/load/switch readback checks without injecting precomputed inner values to fake automatic derivation.

Plan-only feature notes updated; no runtime defaults/code/qualification promotion, current M0 assignment/cursor or Actions dispatch changes. Static links/catalog/governance validation only; product tests remain NOT_RUN for this documentation clarification.

```feature-impact
{"kind":"updated","ids":["path-mtu-budget","tls-auth-multiclient","gui-config-feedback","server-management-cli"],"reason":"Clarify planned outer-only user MTU input and automatic read-only inner MTU across 027A–030; no implementation or evidence status changes."}
```
