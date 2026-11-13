# PLAN029 H1732｜H1731双OS私有V3 ABI与独立FakeIP配额实测结果

- H1731 SOURCE `c5dfb5c9d736f45bae1f52a43405183e2ef942ba` [Windows/Linux Rust Action43397352991](https://github.com/lly8666/wbd-next/actions/runs/43397352991) 全成功：Windows2025 platform 46 PASS、Rust PLAN029 52 PASS，再开`m0_v4_probe` 53 PASS（含精确Rust V3 ABI）；Ubuntu24.04 platform 115 PASS、Rust PLAN029 45 PASS。原H1730失败保留不覆盖。
- [同SOURCE Windows GNU/ARM64 Cross ABI 43397352784](https://github.com/lly8666/wbd-next/actions/runs/43397352784)、native regression 43397352965、R0 ABI 43397352891、ARM64 bundle 43397352914、治理43397352894均SUCCESS，范围详上，均不能替代真实业务网络。
- 当前`NativeSplitWorker`已正确隔离FakeIP身份上限和Direct活动flow限额，高级41地址pool正确提供41次安全预留、42次拒绝；V3 probe Go/Rust布局读回编译纯测试正常，但正式Go仍调用V2，V3未获得产品Ready。
- 正式029 Direct kernel TCP+Defender owned、双DNS socket及原Rust隧道方向、内核UDP DNS/TCP53、FakeIP真回注/重启、原认证owner Stop、D1–D5/P1–P2、padding依旧NOT_RUN；不能用本批绿灯关闭029。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record source-locked two-OS Rust/V3 ABI and GNU cross ABI PASS_SCOPED after H1731 small-pool fix while preserving H1730 FAIL and real product NOT_RUN"}
```
