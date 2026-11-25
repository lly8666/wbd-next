# H2418 targeted diagnosis

H2417 evidence: 21Mbps clean aggregate, server relay DERP-only during initial ping; at 2% BBR socket has median 354135.5 bytes notsent and pacing 818376 bps. No evidence to enlarge pipe. Isolate jitter and infrastructure first. Same production SOURCE except fixture/doc, same Normal/off, MTU1160, outer repair ON, 400ms fixed added RTT, IID 0/1/2/5%, A/B/A′ 30s one stream download (8s omit), independent one-shot origin per leg, origin fq600 and matched BBR, sample both actual socket endpoints. Diagnostic capacity prerequisite both unshaped direct eight-flow directions >=100Mbps and both initial tail pings DIRECT_CANDIDATE (not 800Mbps throughput qualification). If not met, classify infrastructure and stop sweep rather than measure DERP. No changes to proxy algorithm or transport. CUBIC/custom algorithm later only with valid diagnosis.

```feature-impact
{"kind":"none","ids":[],"reason":"Only experiment fixture and evidence changes; no product behavior or defaults changed."}
```
