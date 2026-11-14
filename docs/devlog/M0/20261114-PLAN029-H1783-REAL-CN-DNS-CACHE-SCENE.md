# PLAN029 H1783 | Real Windows CN DNS cache, two app sockets and one physical upstream

- **Signed physical test source staged, NOT_RUN at commit.** One original Windows Go TLS/Rust Wintun owner, two original Windows UDP client sockets with distinct lease-bound source ports and DNS IDs query the exact same CN domain. Both must receive the SAME durable FakeIP; an independent original Linux physical DNS socket can see **only one** target query and returns a real CNAME/A. The existing Direct FakeIP physical UDP echo, Tunnel checks and owner Stop remain mandatory. Ignore unrelated QNAMEs on physical DNS as non-target requests, never count them as a miss, while a second target query fails.
- H1782 native DirectDns cache unit build and H1781 independent Direct8 live Stop run remain source-frozen. This new fixture does not imply DNS cache full/256 transactions full, FakeIP cap, TCP53 product, CPU/p99, GUI1460 or padding.

```feature-impact
{"kind":"none","ids":[],"reason":"Physical signed two-client DNS cache witness added with exact one-upstream and Stop oracles; product source not changed in this commit."}
```
