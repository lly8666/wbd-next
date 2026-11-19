# H2218 — two distinct GitHub-hosted runners, independent NAT-to-NAT gate

Date: 2026-11-19. M0 checked `START_HERE`, `AGENTS`, current cursor and previous H2217 physical PktMon FAIL; no product or Go/Rust source changed.

**User constraint**: client and server each behind a NAT device. Previous H2216 real Linux netns test put all LANs, routers and WBD processes inside ONE hosted runner; that is not independent-runner WAN. New workflow `.github/workflows/qa-h2218-two-runner-nat-preflight.yml` uses distinct Azure-hosted x86_64 and ARM64 runner jobs, x86 private namespace `10.249.21.2` behind host MASQUERADE and ARM64 private namespace `10.249.20.2:443` behind host TCP443 DNAT. Only an ephemeral public-IP/nonce rendezvous is exchanged via an Actions artifact (not a packet relay). The private ARM64 service answered a local nonce challenge. No WBD secrets or raw captures are uploaded.

**Actual Action** [44509653652](https://github.com/lly8666/wbd-next/actions/runs/44509653652), exact workflow SOURCE `07ebb05b4e3cc4faccc01c9349373f91b945fc44`: ARM64 server job SUCCESS, x86 client job FAILURE from expected fail-closed network assertion. Four direct public TCP443 connection attempts each timed out. Client iptables SNAT counted **4 packets / 240 bytes**; server's PREROUTING DNAT rule counted **0 packets / 0 bytes**. Server logs show READY and only local private challenge. Thus the failure is before the actual WBD application. Hosted Azure public egress IP is not proof of an independently ingress-routable endpoint; an upstream network policy/public NAT mapping is a plausible blocker, not an established specific root cause. Workflows earlier [44509437042](https://github.com/lly8666/wbd-next/actions/runs/44509437042) and [44509491954](https://github.com/lly8666/wbd-next/actions/runs/44509491954) failed x86 job setup due invalid checkout action SHA, not network tests; corrected by pinning actual upstream `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`.

**Qualification**: `BLOCKED_NETWORK_PREREQUISITE`, WBD original-Go TLS/Rust Native DATA/ACK/TUN/Stop **NOT_RUN**, physical Windows/Npcap **NOT_RUN**. This result cannot explain the physical H2217 trace where original TLS ALREADY succeeded but Rust RXDelivered stayed zero. Do not relabel either H2216 scoped Linux NAT PASS or H2217 physical FAIL. No repeated cloud ingress runs or weak-network matrix without new routing capability. Next meaningful test requires a truly inbound-reachable service-side public port-forward on self-hosted runner (or authorized transparent L3 transport) plus client-side SNAT, with exact SOURCE/driver and bounded Go→Rust and server TX counters.

Evidence: [H2218 exact live Action and NAT counters](../evidence/M0/PLAN029-H2218-TWO-RUNNER-NAT-PREREQUISITE-FAILED-20261119.json).

```feature-impact
{"kind":"none","ids":[],"reason":"New QA workflow, environmental network qualification and M0 records only; no production protocol, config or feature-card changes."}
```
