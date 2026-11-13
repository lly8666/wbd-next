# PLAN029 H1768｜H1767被便宜门拦截，不重跑旧028／不提前认定产品失败

- H1767 `8232d7d40468fa35e6cb14a4f54bc4aa979b232c` 的 [签名工作流43525950546](https://github.com/lly8666/wbd-next/actions/runs/43525950546) 尚未实际执行Windows↔WSL2业务：单条`tests.test_m0_plan029_h1749_signed_direct_order`测试断言里误将换行写为字面`\\n`，实际 runner 有` stop_windows(w);stop_linux()`并位于H1767 D1黑洞之后。修复只校验真实末尾Stop顺序，避免测试字符串错配。
- [功能卡治理43525950582](https://github.com/lly8666/wbd-next/actions/runs/43525950582) `dns-split-ipv6: unknown verification status`：新H1766真实签名PASS行用了不在catalog状态枚举中的`PASS`，改为严格允许的`PHYSICAL_PASS`，保留精确SOURCE与artifact。绝不改变H1766的真实全绿，也不把H1767未运行的黑洞写成PASS。
- 新DNS黑洞工作只在**一次**真实Windows/Wintun+Linux/TUN里观察Tunnel query≥2、Direct physical query=0、Windows无意外答复，仍待执行。H1767的Windows2025 Rust组件另报 **E0277**：新`v4_windows_owner.rs`单测误用`drain_tx(...).unwrap()`，其Err含不实现Debug的`TxDispatch`；仅改测试为`unwrap_or_else(|_|panic!(...))`，不修改生产TxDispatch或M1/AEAD。Linux组件PASS，Windows新SOURCE待重跑。原M1 padding方法未接冷配置/实际Tunnel/GUI，不准宣传为真实padding功能启用。
- H1768冻结源码后等独立组件收齐，提交同一签名marker单Normal来源；不手动重复dispatch；保留旧028测试场景和030关闭。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1768 fixes unsupported PASS status into PHYSICAL_PASS for existing H1766 source-scoped signed evidence; H1767 actual scenario still blocked by cheap test"}
```
