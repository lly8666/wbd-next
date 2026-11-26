## ACK3 scoped native functionality recorded

Candidate 8a6439b exact run45821912474 both ISAs actual Normal functional PASS, both ZIPs independently reviewed; main evidence https://github.com/lly8666/wbd-next/blob/916214d40dc43e9e78cf9d28a1f7ec0be2dc6946/docs/evidence/M0/20261126-DUAL-RUST-TCP-ACK3-NATIVE-FUNCTION.json. Feature remains experimental, performance in flight. Dedicated full TCP core tests pinned to the same candidate (no binary rebuild for performance), including new ACK3/timer/gap test, not yet run.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Record ACK3 exact dual-ISA native functionality; preserve experimental status and in-flight performance scope."}
```
