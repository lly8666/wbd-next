# PLAN027A H922｜中断恢复与首批 Rust/Go 冷预算（recovered）

恢复 main `ecf77e78cd0b12b82e51a9d9f614aa96b59137d6`；H920 的 PLAN027 是用户限定范围结案，旧 FRC/CPU/p99/Action FAIL 原封不动。开工时无在途 Action；本次 main 自动 push CI 不是额外手动 dispatch。

首批已实现：Rust FrameBudget 对原始 peer SYN MSS 按实际 DATA IPv4/TCP options 计算，Game+FEC2 typed 1B 单独预留；1500 完整外层 IPv4/20+20 下 1398 为单 IP cap，1399 不允许单 record。新 `wbd_m0_v4_mtu_budget_v1` 为无 TLS/OS 状态的版本化 C ABI，Go Linux pre-TLS SYN offer 与认证后内层预算消费同一 Rust 输出；Linux owned TUN 真实 `ip -j` readback，不把 planned 日志当 applied；公开 outer ≤1500，jumbo 不宣称可用。

SOURCE `ecf77e78cd0b12b82e51a9d9f614aa96b59137d6` 的 r0-record-wire、wire-codec、r0-v4-cold-native、r0-cross-abi（Windows cross + ARM64）、r0-link-fec-mtu 为**编译/单元域 PASS**，并不证明真实 OS/Wintun 原生应用包。治理 `41432365461` 因缺本 devlog/卡片声明 FAIL；Normal-common `41432365444` 在不带 fec2_product_record 编译时原有 dead_decision 缺 cfg-off 分支 FAIL。本批补严格无-FEC false 分支、补卡片和声明；旧 FAIL 不逆转，待新 SOURCE 测量。

仍需：Windows outer/inner 错传和默认1400帽、真实双向 OS 读回、DF0/DF1 分片与反馈、有限 native 7-mode/ARM64/弱网/保护性能，均明确 NOT_RUN。详见 `docs/evidence/M0/PLAN027A-H922-SOURCEECF77-ACTIONS-20261102.json`。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"H922 first actual PLAN027A Rust GameFEC typed 1B+MSS options oracle, versioned Go cold ABI, Linux OS applied MTU readback and public <=1500 range; mark cross build only, retain Windows/DF/native NOT_RUN."}
```
