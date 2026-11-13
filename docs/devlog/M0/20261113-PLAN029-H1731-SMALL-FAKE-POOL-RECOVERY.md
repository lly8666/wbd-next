# PLAN029 H1731｜H1730真Windows失败：高级小FakeIP池容量边界

- SOURCE `1d0458a8fdff21b450b4b05a272f0f1667aa24e9` [Action 43396935678](https://github.com/lly8666/wbd-next/actions/runs/43396935678)：Linux 029 Rust scoped PASS；Windows 029 Rust 51 PASS、1 FAIL，首错`plan029_native_cold_policy_rejects_fake_range_overlap_or_wrong_dns` 的高级 FakeIP 池 198.18.1.4..1.44 （41槽）被错误固定 `max_entries=60000` 拒绝，无法到V3 ABI后续测试。保留原FAIL日志。
- FakeIP 60k是**硬上界**，不是每个pool必须拥有60k：按inclusive实际池宽夹紧 `min(60000,pool_width)`，完全不以Direct活动流hard cap决定；新的41分配/第42拒绝用例也证明仍无法挤掉活映射。16MiB字节上限与写前不得发布FakeIP不变。
- 当前提交仅源修与定向回归，Windows/Linux/V3测试待新SOURCE运行，产品双出口/DNS/Stop/padding仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Fix Windows scoped Rust regression: advanced 41-address FakeIP pool must cap independent 60000 identity quota by actual pool width, and test 41/42 boundary"}
```
