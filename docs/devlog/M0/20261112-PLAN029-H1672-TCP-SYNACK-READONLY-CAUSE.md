# PLAN029 H1672｜H1669 no-SYNACK focused read-only Windows diagnosis

- SOURCE H1671 cursor preserves H1669 real signed Windows TCP kernel SYNACK missing **FAIL**, action 43216324767. One scoped rerun uses existing original signed Wintun test setup, IP Helper exact /32 owned local route+lease and native Win32 TCP listener.
- Before injection, perform one **real Windows same-host native TCP dial+accept** to that same listener, and **read-only** Windows adapter network category plus current firewall profile enabled/default inbound policy. Then use original raw IPv4/TCP SYN and true Wintun RX ring and log matching TCP frame flags (including RST) and first missing step. No WFP/Defender rule creation, no changing firewall profiles, no external probing, no mock packet delivery.
- If listener accepts locally but ring raw SYN cannot produce SYNACK and profile inbound denies, record supported OS/default-inbound implication without claiming packet drop causal proof. Do not loosen firewall; contract §3 Direct-only Rust stack is alternative only when hard Windows feasibility is evidenced, not yet selected.
- Exact source [H1669 failure](https://github.com/lly8666/wbd-next/actions/runs/43216324767) remains, new H1672 action is one bounded OS scene, no 028 matrix.
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1672 source-locked signed Windows no-WFP Direct TCP kernel gate adds only real listener self-connect and read-only firewall/ring flags diagnosis after H1669 FAIL."}
```
