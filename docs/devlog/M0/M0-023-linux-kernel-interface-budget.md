# M0-023 local kernel interface MTU integration

CODE SOURCE: d77570ec70ef779659d5e48c67785b4db1adf776.

Normal Rust ScopedOwner now derives Normal/off TX sizing from Linux kernel's local interface name/index/MTU observation together with the original protected Go V4 SYN peer MSS. In-process native Go client independently authenticates Rust output for three cipher suites. No network device sends or receives business packets here.

Exact Actions: native owner https://github.com/lly8666/wbd-next/actions/runs/38835966447 PASS, five Go top-level tests, Rust 1/1. Native functional platform 76/76 PASS in run 38835966387. ABI, cross builds, Governance and G2 PASS. Maintenance run 38835966509: 169/169 PASS.

Remaining: production authenticated native installation, route PMTU, actual TUN/raw application I/O, kernel driver loan Stop B01-B04, physical E2E and performance NOT_RUN. Production features=0. Next integrate private protected Go owner control with actual M4 driver lifecycle.
