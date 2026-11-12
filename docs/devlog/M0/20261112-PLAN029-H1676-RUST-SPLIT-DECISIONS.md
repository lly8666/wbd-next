# PLAN029 H1676｜Rust shared IP/DNS/FakeIP decision logic, not network qualification

- Reuse same wbd-engine crate and existing G2 Rust build. Add `v4_client_split` as one shared cold-compiled decision core for later Normal/Game Wintun ingress dispatch; **no product activation or second Go hot path**. Explicit modes `all|bypass-lan|bypass-lan-cn`, sorted/merged IPv4 intervals O(log N) lookup and no CIDR→OS route expansion.
- DNS internal purpose takes precedence over destination IP: bootstrap/internal-direct **Direct**, internal tunnel **Tunnel** even if upstream lies in CN/LAN ranges. Ordinary CN-domain DNS direct only under CN mode, otherwise tunnel. No DNS backup/fallback code.
- Selective FakeIP returns only the mapping's real IPv4 as physical Direct; unknown reserved fake IP fails closed (never physically leaked or sent tunnel). Real non-CN IP of shared CDN remains Tunnel unless independently CN-IP. Per-flow pin retains destination and decision until explicit close/idle; no 30-second renew.
- Small exact/suffix domain trie enforces label boundary and lowercase ASCII; reject unimplemented keyword/regex domain sources **loudly** rather than silently treating as suffix. Full v2fly snapshot+keyword/regex and source-persistent mapping, real DNS dispatcher, async Direct TCP/UDP and ingress ABI are **NOT_IMPLEMENTED**, so D1–D5/P1–P2 remain OPEN.
- Five pure tests execute in G2 existing Rust build target for this SOURCE, reuse its build; no real Windows socket/Wintun or TLS claimed. Previous SOURCE cc4b H1675 [Go source Action 43221547201](https://github.com/lly8666/wbd-next/actions/runs/43221547201) and [GUI Action 43221547196](https://github.com/lly8666/wbd-next/actions/runs/43221547196) SUCCESS scoped, while H1672 real Wintun TCP H1672 FAIL persists.
- Latest no-WFP decision remains authoritative: delete old WFP guard/stages from actual lifecycle before claiming signed networking; this Rust pure core is not a substitute.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add shared Rust cold compiled IPv4/CN-domain/FakeIP/flow-pin policy, DNS owner-purpose override and G2 source-only unit tests; E2E remains unqualified."}
```
