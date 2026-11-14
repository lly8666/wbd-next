# PLAN029 H1787 | full Tunnel DNS table fails only original request

- Native `TunnelDnsMap` already caps in-flight UDP DNS purpose tickets at 256. On full/collision the original Rust Wintun TX `TunnelDns` rewrite previously just dropped the request, causing app timeout instead of the contract's prompt local failure. When rewrite rejects a valid captured app request, the exact original unmodified L3 packet now goes through one bounded `DirectDns::fail_tunnel_query` **reply-only** builder: DNS SERVFAIL, original ID/port, original app-visible DNS address, own Wintun reverse mailbox. **It does NOT open a Direct DNS socket or cross-resolver retry.** A mailbox full can still drop the affected UDP response, never block Tunnel DATA.
- Rust unit builds a real IPv4/UDP DNS question, asserts error return tuple/ID/status, no cache/inflight socket and refuses foreign lease. Same owner fairness/reverse queue, no WFP, no per-query OS thread, no wait. H1786 genuine physical scene runs independently at its own SOURCE. Separate native small-capacity/full table pressure and Stop **NOT_RUN** on this source; D1 TCP53/P1–P2 remain open.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Actual Tunnel DNS table-capacity rejection now surfaces local original-client SERVFAIL without any cross-exit fallback."}
```
