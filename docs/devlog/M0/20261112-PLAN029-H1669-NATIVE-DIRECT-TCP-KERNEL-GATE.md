# PLAN029 H1669｜signed Windows Wintun Direct TCP kernel feasibility gate

- CONTRACT §3 requires one real Windows minimum gate **before** choosing kernel-local Direct TCP relay or mature Rust TCP fallback. This tests the old signed original-Go Windows Wintun+Win32 IPHelper baseline on Windows2025 with original vendor Wintun 0.14.1 SHA256 lock.
- One test-only /32 Wintun lease and one exact original IPHelper reverse route, both owned and cleaned; inject original on-wire IPv4/TCP SYN, observe Windows SYNACK from real Wintun ring, complete ACK→native accept→payload→native response via ring→FIN. No old project WFP guard, no firewall setting/rule change, no mock NPF/Wintun, no production Applied receipt, no packet data leaked in final artifact. Preserve failure if OS Defender blocks kernel listener.
- Explicit scope: Windows signed native kernel listener feasibility only. No physical external TCP leg, no Rust async relay, no CN FakeIP, no two DNS real egress, no production credentials/TLS or OS WAL. If this gate fails, inspect first actual OS failure before selecting alternative; no speculative implementation of two backends.
- Source locked to new GitHub Actions workflow and tool-only test file; no new PLAN028 matrix or arbitrary real deployment.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"PLAN029 signed Windows single Direct TCP kernel ingress feasibility action added; record NOT_RUN until actual receipt, no Rust Direct TCP claim."}
```
