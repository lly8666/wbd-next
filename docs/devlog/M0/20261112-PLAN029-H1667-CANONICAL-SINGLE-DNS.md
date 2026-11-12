# PLAN029 H1667｜two canonical single DNS and no fallback cold bootstrap

- Source: Windows Go CLI + config catalog + original WinForms portable profile import + original physical Npcap bootstrap updated as one pinned overlay manifest. `dns.direct=223.5.5.5`, `dns.tunnel=1.1.1.1`; each only one IPv4, port53. `dns4` is input-only migration (first entry→tunnel DNS if no explicit new key, report discarded entries; conflicting new key rejected). GUI hides deprecated field and saves just two single values.
- Domain cold generation resolves using ONLY configured `dns.direct`; NIC resolver enumeration, default 1.1.1.1/8.8.8.8 fallback and multiple DNS attempts removed from selected source. Old literal IPv4 still does not resolve; TLS authenticated SNI and offline route-key remain separate; default outer MTU=1460B and auto inner read-only.
- **NOT native network qualification:** old host OS DNS stage receives ONE tunnel address; true Rust Wintun QNAME dispatcher, FakeIP for CN domains, Direct TCP/UDP reverse path, explicit no-old-WFP product transaction, actual origin Windows DNS/WAL and signed GUI E2E remain OPEN. The old source-only H1661/H1663 actions do not qualify this new SOURCE. No 028 seven-mode retest.
- This batch intentionally does not switch network Applied to a fabricated guard-free receipt or use Go per-packet hot pump. First verify current Go source/native WinForms build, then genuine signed Windows Direct TCP ingress feasibility and new fixed owned 4-stage path separately.

```feature-impact
{"kind":"updated","ids":["client-domain-bootstrap","dns-split-ipv6","gui-config-feedback"],"reason":"PLAN029 latest single resolver semantics: Windows CLI/WinForms canonical direct/tunnel DNS, legacy dns4 migration, physical Npcap bootstrap uses only direct; real native D1-D5 still NOT_QUALIFIED."}
```
