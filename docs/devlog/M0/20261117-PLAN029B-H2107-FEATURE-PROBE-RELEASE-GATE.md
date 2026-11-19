# PLAN029B H2107｜带 m0_v4_probe 的 Windows release 门与三处旧诊断跳包枚举

回查原 [H2106 Action44096919880](https://github.com/lly8666/wbd-next/actions/runs/44096919880)，SOURCE `0956c04ca4ba87201e2229bb701fa24bca734385`。Cheap workflow、Windows Go、Linux Rust 和 **Windows Rust 普通库单测**均 PASS；原 Linux Rust/Go 两端编译成功，进入签名 Win2025 original Rust release DLL 时 FAIL：`rustc E0004`，分别在 `v4_windows_plan029_udp_gate.rs:82`、`tcp_gate.rs:87`、`dns_gate.rs:62` 的旧 PLAN029 **非产品** `m0_v4_probe`诊断 gate；H2105 新内部 `ReadResult::SkippedIpv6` 未入三个穷尽匹配。**驱动/AF_INET6/IPv4混跑和 Stop 均 NOT_RUN**，不归因于IPv6真实拦截。

修复仅在三个旧 gate 的原`Skipped`匹配添`SkippedIpv6`：UDP/DNS保持原 bounded wait，TCP保持原 break；不用新解析、全局路由、业务容器或Go per-packet。扩展 `tests/test_m0_plan029b_b3_ipv6_scope.py` 明确验证三个 gate 的 `cfg(feature="m0_v4_probe")` 和跳包处理、以及 Windows preflight 的 release probe-feature `cargo check`。此前普通 `--lib` 不编诊断 gate，误放过；本次在 Windows Rust廉价job中**先**`cargo +1.85.1 check --locked --release -p wbd-engine --features m0_v4_embedded_go,m0_v4_probe,fec2_product_record --lib`（不需要签名驱动/Npcap也不带额外ISA-L静态链接）。真正签名Action仍继续用生产固定 `native_fec_acceleration` 真实release DLL和原厂WinForms/Go/Rust/TUN/WAL。

本次仅触发**廉价同源预检**，并不直接重复B3原生测试。预检通过才在后续独立SOURCE用**唯一一次**显式`[plan029b-b3-ipv6-real]` 恢复真实发包。H2098 CN普通与H2101先进CN真签名、H2103 off签名和H2104 GUI冷配置仍仅限对应旧SOURCE。B3原始 /128 IPv6+IPv4物理未验，B4多代/Game和B5同VM<=10Mbps CPU/GiB/p99仍待验。不重开028或030。

```feature-impact
{"kind":"none","ids":[],"reason":"H2107 only 3 old Windows m0_v4_probe diagnostics enum exhaustiveness and preflight exact feature release cargo check; feature status unchanged"}
```
