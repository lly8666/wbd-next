# PLAN029 H1788 | Tunnel DNS question identity cannot be stolen

- Existing 256-ticket `TunnelDnsMap` matched resolver source, original UDP port and DNS ID but not the echoed QNAME/QTYPE. A forged or unrelated response could consume a valid pending ticket. On real DNS/53 **only**, store the original parsed lowercase QNAME and QTYPE at request admission. Reply requires QR=1, QDCOUNT=1, same QNAME/QTYPE, and original ID before rewriting source or retiring ticket. Wrong reply is dropped and correct waiter remains alive; no fallback, second DNS socket, global DATA parser, background thread or unbounded retention.
- The original DNS question parser gets a read-only response companion sharing identical bounded name rules. Rust regression checks wrong name/type followed by accepted original reply. Full native signed poisoning scenario and owned Stop for this new SOURCE **NOT_RUN**. H1786 signed cache+Direct8 native proceeds on its earlier frozen SOURCE. D1 app TCP53/P1–P2 remain open.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Strict original QNAME/QTYPE identity on Tunnel DNS responses before ticket retirement."}
```
