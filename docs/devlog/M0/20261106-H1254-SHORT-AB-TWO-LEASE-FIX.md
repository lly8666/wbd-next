# PLAN028 H1254 — fixture-only lease cardinality repair

H1253 source 68146e914daf3b64ab46dfff62e0420c05214c22 Action42124162759: genuine native x86 pinned ISA-L v2.31.1 built and linked into current Rust product; actual `ec_encode_data` archive/linked ELF symbol was present and Rust late fully-delivered FEC repair regression passed. Original Go protected TLS server and 2 separately authenticated client /32 leases **10.66.0.192 / 10.66.0.141** successfully reached real Ready; no user business was sent yet. Diagnostic failure was Python orchestrator line213 still asserting exactly five independent leases despite changing matrix to Game4+Normal **two** clients.

Change **only** `assert len(set(leases)) == len(NAMES)`, keeping true distinct live leased identities. Rerun one same-VM 90s/leg scalar/native with same bounded netem 10000, 15% loss100ms, 40s sustained/20s overload/25s rate-down recovery, one Normal sibling and exact backend counters. This is a test-harness FAIL, not an application performance result. No product source, protocol, queue or FEC parameter changes at H1254.

```feature-impact
{"kind":"none","reason":"Fix wrong 5-vs-2 authenticated lease expectation only in pre-traffic native A/B harness, no product runtime changes."}
```
