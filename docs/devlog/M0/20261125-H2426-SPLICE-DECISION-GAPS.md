# H2426

H2426 frozen product 559f2093857919c6293ee6f85622b55f198251fc, build45556602991 artifact14995813926. Eight independent single scenario ABBA/BAAB tests: 5% mild NAT vs splice both TUN default qdisc; 30% maximum NAT vs splice both default qdisc; 30% maximum NAT vs splice explicit fq600 with actual bidirectional 600Mbps netem rate, 400ms added RTT, 16000 packet queue; mixed clean NAT explicit fq600 vs kernel default with actual 100 small TCP and 400 UDP roundtrips offered during single bulk stream. Probe deadlines and late schedules explicitly recorded; P99 of successes not substitute for loss. No default change, no CC changes; local netns not physical or 3-runner. Retain failed/incomplete data. H2425 evidence docs/evidence/M0/20261125-H2425-MATCHED-FEC-HIGH-LOSS.json.

```feature-impact
{"kind":"none","ids":[],"reason":"Frozen product decision-relevant diagnostic fixture and evidence only."}
```
