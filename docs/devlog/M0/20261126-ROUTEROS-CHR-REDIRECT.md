# RouterOS normal scoped acceptance and opt-in redirect

1762401 real normal routed/DNAT PASS_SCOPED; nft TPROXY FAIL before client. Next source tests six DNAT modes, CUBIC REDIRECT and legacy TPROXY. See [decision](../..//decisions/M0-ROUTEROS-SERVER-20261126.md) and [evidence](../../evidence/M0/20261126-ROUTEROS-CHR-NORMAL-SCOPED.json). No parent/main changes.

```feature-impact
{"kind":"updated","ids":["linux-tcp-splice-proxy"],"reason":"Explicit opt-in redirect ingress uses NAT original destination and original Rust splice owner; default tproxy unchanged."}
```
