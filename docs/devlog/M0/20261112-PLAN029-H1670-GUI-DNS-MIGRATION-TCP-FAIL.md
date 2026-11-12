# PLAN029 H1670｜current real WinForms/Go CLI single DNS migration source test

- Extend existing Windows2025 WinForms + real native Go `--check-config` harness with two visible DNS fields and hidden `dns4` legacy alias. Preserve 1460 outer/automatic read-only inner and domain≠SNI checks.
- Source-locked validation: default direct 223.5.5.5 and tunnel 1.1.1.1, old `dns4=9.9.9.9,8.8.8.8` imports only first into tunnel and persists no secondary, conflict with canonical tunnel is rejected, portable reopen retains values. Exactly one GUI/CLI configuration Action, no new signed network assertion.
- H1669 SOURCE bd82a8 [real signed Windows test](https://github.com/lly8666/wbd-next/actions/runs/43216324767) **FAIL**: signed Wintun and owned /32 route set up, but synthesized SYN got no kernel SYNACK within 6s with no product WFP/Defender rule. Record FAIL, investigate read-only Windows inbound filtering versus route / local TCP capability before choosing any secondary stack. Do not call H1669 Rust Direct TCP product PASS.
```feature-impact
{"kind":"updated","ids":["gui-config-feedback","dns-split-ipv6"],"reason":"H1670 source-locked real GUI/CLI single-DNS migration harness and preserved H1669 signed Wintun kernel TCP SYNACK failure."}
```
