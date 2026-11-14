# PLAN029 H1793 | owned kernel TCP/53 integration and H1791 recovery

- Collected [H1791 native Action 43552619098](https://github.com/lly8666/wbd-next/actions/runs/43552619098), source `7f6b23f57aa5d4e8ce6a80b496d14faa79d09c74`: SUCCESS true Windows Wintun / Linux TUN default outer 1460, auto inner 1389 on both OS; Direct/Tunnel TCP/UDP, single DNS and original owned Stop PASS. Evidence: `docs/evidence/M0/PLAN029-H1793-H1791-REAL-DEFAULT1460-AND-ABI-SPLIT-20261114.json`.
- Distinct H1792 original Go ABI [43553082256](https://github.com/lly8666/wbd-next/actions/runs/43553082256) FAIL: original pinned ClientConfig has no RootCAs member in overlay tests. The Rust DLL and Rust source gates passed. Leave this red OPEN, no insecure TLS workaround.
- H1793 SOURCE ONLY, new real native TCP53 NOT_RUN: Wintun original app TCP/53 is mapped onto the existing after-Apply kernel Direct listener, reverse NAT through single Rust Wintun TX. Direct NAT ports 32768..49151, independent bounded DNS ports 49152..64000 with 256 outstanding max. Accepted client TCP stream uses the bounded H1792 QNAME transaction; exact direct physical-bound or Tunnel Wintun-lease-bound DNS/53 endpoint, same IP across fields supported by different source/ifindex. Live internal Tunnel DNS TCP source port registration bypasses recursive capture, no new WFP, Wintun reader, Go pump or per-flow worker. Original FakeIP durable persist precedes CN A reply.
- New SOURCE Rust compiler gates and actual original Windows application TCP53 two-OS delivery+Stop are necessary before D1 PASS. D3 tables/D4 OS recovery/IPv6/D5 live GUI and P1/P2 mixed performance/padding OPEN.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-only new TCP53 product integration, not yet independently compiled or physically qualified on H1793 SOURCE."}
```
