# PLAN028 H1190 — ARM post-auth packet-loss heredoc receipt alias

The H1189 newly generated native ARM test reuses qualified x86 true UDP/RTT measurement source, whose final Linux network-owned JSON receipt has a pair of `PY_H1178_END` heredoc markers. H1189 fixture asserted no legacy delimiter remained but did not rename it. Correct the **test-only marker name** to `PY_ARM_NETEM_END` during generation; this affects neither Linux packet generation nor actual qdisc semantics, Go/Rust or wire. Run one native ARM/ARM Action. H1189 earlier in-flight native Action may fail at fixture setup and is not a product failure. x86 physical netem5 and signed Windows protected Game4 cohorts already scoped PASS, H998/ICMP/Android/CPU causal limits retained.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix only generator heredoc alias before an otherwise deterministic pre-native fixture assertion; no product/runtime change."}
```
