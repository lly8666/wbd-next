# H2440 scoped close

H2440: docs/decisions/M0-H2440-WEAK-LINK-RESEARCH-CLOSE.md; H2439 all22 jobs/84 rows measured and drained, all BBR explicit-cap local full drops zero. All logs reviewed, four original ZIPs inspected. Burst and down-only BBR clear gains, ACK-only both good; shared competitor throughput lower with BBR, cap mitigates but not equal fairness. Jitter+reordering both CCs collapse to few Mbps, deferred explicit limitation; no root cause confirmed. Evidence docs/evidence/M0/20261125-H2439-REALISTIC-WEAK-LINKS-REVIEW.json. Retain architecture and stop weak-link/CC optimization per user, no new code/run. No v3/plus tested, no production promotion, H2438 release gates remain.

```feature-impact
{"kind":"none","ids":[],"reason":"Record scoped weak-link review and deferred jitter limitation; no product change."}
```
