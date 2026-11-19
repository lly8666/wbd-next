# H2214 | Client-side TLS certificate-verification switch
User requested default OFF, opt-in true. Linux: --tls-verify-server bool; Windows: original Go CLI + WinForms GUI Bool; Native Normal/Game2/Game4 use the same TLSVerifyServer policy. Only client cold config changes. Server TLS, Decoy, route-key and Rust dataplane unchanged.

SECURITY: Default OFF keeps TLS encryption but disables server identity verification. Active impersonation can expose protected admission credentials. Recommend --tls-verify-server=true with explicit trusted certificate/CA PEM.

QA branch qa/h2214-client-tls-verify-switch-20261119 based on 46a756df1114aecda8dc2d5d259a5cbb4c9a909f. Action tests include native Linux x86_64/aarch64 source build, Go parse tests and Windows CLI/WinForms GUI compile/selftest. H2214 source-locked Actions 44470462032 PASS (Windows original Go/WinForms 419 self-checks, native Linux x86_64 and ARM64 Go/Rust jobs all SUCCESS). Independent original Go TLS handshake regressions cover default OFF with self-signed server, explicit ON rejection of untrusted self-signed certificate, and explicit ON success for locally trusted certificate. Evidence: docs/evidence/M0/H2214-CLIENT-TLS-VERIFY-SWITCH-SOURCE-ED1370-ACTIONS-20261119.json; run: https://github.com/lly8666/wbd-next/actions/runs/44470462032. Physical Windows-to-ARM64 WAN, 32 live clients, DPI and p99 remain NOT_RUN; no production release claim.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H2214 client TLS validation default-off user request wired to Linux CLI, Windows CLI, WinForms and native Normal/Game paths, with bounded QA"}
```
