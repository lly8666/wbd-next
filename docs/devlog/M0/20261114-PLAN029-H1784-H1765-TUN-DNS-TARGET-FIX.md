# PLAN029 H1784 | first real H1781 H1765 DNS fixture boundary

- Source `deafbbe9d04166692be5cd33e1883cac07cd111a`, [signed Action 43546818820](https://github.com/lly8666/wbd-next/actions/runs/43546818820) native job 132301513315 **FAILED** after real CN FakeIP Direct UDP + TCP32K and ordinary Tunnel TCP/UDP PASS_PRE_STOP. First recorded failure is Linux H1765 Tunnel DNS/53 `foreign or unexpected real tunnel DNS QNAME/peer` followed by Windows nonCN target DNS timeout. The old fixture combined source+QNAME in one assertion, so which field diverged is **UNKNOWN**; no product DNS or firewall root cause inferred. H1781 hard8 and owned Stop were NOT_RUN after this boundary. Evidence `docs/evidence/M0/PLAN029-H1784-H1781-H1765-TARGET-FIRST-FAIL-20261114.json`.
- H1784 fixture-only repair: bounded <=64 unrelated QNAMEs silently ignored on genuine Linux TUN/53, one 26s absolute deadline, exact requested target DNS question *still* requires authentic client lease; send one response solely from `1.1.1.1` to the original client. No new resolver, OS route, WFP, global fallback, or duplicate Wintun. Pure predicate regression verifies different QNAMEs are ignored and target/lease validations remain.
- Efficient combined signed Next Action enables **H1781 Direct-hard8 capacity+idle recovery** and **H1783 two Windows DNS clients one Linux physical CN DNS upstream** under one original Windows signed Wintun owner, keeps normal owned Stop mandatory. H1783 prior independent SOURCE is not claimed green by this fix; D1 TCP53/D3 resource full/D4–D5/P1–P2 remain OPEN.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked test-only shared Tunnel DNS target filtering, no production setting or new product qualification."}
```
