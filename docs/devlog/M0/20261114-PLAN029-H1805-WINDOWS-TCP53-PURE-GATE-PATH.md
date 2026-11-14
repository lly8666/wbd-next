# PLAN029 H1805｜TCP53 确切 SOURCE 原生组件验收的 workflow 路径缺口

- H1804 `b23d74298fd639a1eec3926c24cce020041cccf6` [cross-ABI Action43563253326](https://github.com/lly8666/wbd-next/actions/runs/43563253326) Windows x86_64 / Linux arm64 双 target BUILD SUCCESS、[governance43563253254](https://github.com/lly8666/wbd-next/actions/runs/43563253254) PASS、[native-functional43563253275](https://github.com/lly8666/wbd-next/actions/runs/43563253275) PASS。但 native-functional 的 136 engine 通过是其它筛选用例，**未运行新 FakeIP 两项 plan029_**。
- H1803 `301dddab` 的 [PLAN029 Rust 组件 Action43562854910](https://github.com/lly8666/wbd-next/actions/runs/43562854910) Linux 50 plan029_ tests PASS，包括 `plan029_fakeip_multi_a_quota_rollback_preserves_held_and_recovers` 与 `plan029_fakeip_failed_multi_a_does_not_erase_prior_uncertain_journal`；Windows E0609 FAIL 仍保留。
- H1804 的 TCP53 E0609 修复并未触发同一 PLAN029 纯组件 Action，原因是 `.github/workflows/m0-plan029-h1721-native-split-capacity.yml` 的 push paths 缺少 `v4_windows_native_dns_client_tcp.rs`。本次只补准确路径，触发一个同 SOURCE 的 Windows+Linux Rust `plan029_` 纯单测工作流，不派真实 Wintun 场景、不恢复旧矩阵、不靠交叉编译冒充运行时测试。
- D3 真实小额度多A恢复与 DNS 黑洞/TC1、D4 IPv6/部分 Apply、D5 GUI effective、P1/P2 队列/CPU/p99 均继续未完成。

```feature-impact
{"kind":"none","ids":[],"reason":"Only add missing exact Rust native DNS client TCP path to existing PLAN029 pure-component on-push test; no runtime or product configuration change."}
```
