# PLAN028 H1121 — Real Windows WSL2 test-owned IPv4 source change and UDP preflight

The earlier H1118 Windows test-owned Hyper-V internal NIC emitted genuine native IPv4/route notifications and OS source selection but had no reachable backend. This isolated **Windows WSL2 underlay preproduct** test boots pinned authentic Ubuntu WSL2 kernel and adds only test-owned host aliases 198.19.254.1 and 198.19.254.9 /24 plus guest eth0 198.19.254.2 /24. Only owned .1 has SkipAsSource changed, leaving original host WSL IPv4, guest IPv4, default gateway, runner-management uplink and DNS unchanged. Read genuine Windows Find-NetRoute selected source from .1 to .9 and demand real guest UDP echo from two separate Windows socket binds. Exact-owned WSL Hyper-V UDP firewall and aliases are cleaned after the scenario. No fake Npcap/TLS or simulated inner packet.

One Action, not full product: until the real original Go TLS/Npcap/Wintun/Rust generation uses this underlay, no Windows product handover PASS. H998 old MTU hot-shrink FAIL, old ARM64 Game4FEC Action FAIL, remote ICMP and CPU/p99/Android NOT_RUN unchanged.

```feature-impact
{"kind":"none","ids":[],"reason":"H1121 one bounded real Windows WSL2 owned source4/UDP underlay fixture, no product Go/Rust source changed."}
```
