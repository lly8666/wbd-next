# PLAN029 H1985｜修 H1984 工作流真实 YAML FAIL

- 原 SOURCE `3257b9e817f374782adeacf9be3c6fc7b19abcda` 的 [H1661 Action43826342300](https://github.com/lly8666/wbd-next/actions/runs/43826342300) **FAIL/零job**：新增的两个 `TestPLAN010` 真实 **NOT_RUN**。原 [maintenance43826344589](https://github.com/lly8666/wbd-next/actions/runs/43826344589) job133160985242 **FAIL**，PyYAML ParserError line86 col2 多了未缩进 `-v ...`，且 line50 selector 被截断、后半份 YAML 复制。[治理43826344472](https://github.com/lly8666/wbd-next/actions/runs/43826344472) structure job133160985939 PASS，FeatureCatalog job133160986306 **FAIL_YAML_PARSE**；原失败留存。
- 查明原因是编写 H1984 时使用 JS `String.replace(old,replacementText)`，而 `replacementText` 中 Go anchored regex 包含字面量美元符号紧跟单引号，触发 JS **匹配后缀替换**（非GitHub故障）；本次用回调式字面量插入，从 `57b2fe47...` 已通过的 86 行 H1661 还原，仅插入两条分别检查退出码的纯 Windows Go 测试调用，90 行、无重复/旧代码改写。
- 一个SOURCE/一个H1661 Windows CI原工序：保持 `TestPlan029` 原单测、单条精确owned Defender COM CAS、编译和NOT_SIGNED_E2E receipt。追加 `TestPLAN010NativeReadOnlyDiskStatusAndConflict` 和 `TestPLAN010OriginalNativeRecoveryNoShellOrLegacyFallback`；只临时磁盘侧证，无防火墙大范围动作、真实网络不派发。
- H1985 SOURCE Go/Actions **NOT_RUN** 直到原push结果；H1983真实Go/Rust编译与新冷拒绝/单条COM规则有限PASS不等于产品功能完成。H1978原native FAIL/H1974真实五次61ms延迟及D1–D5/P1–P2/GUI/Game4/IPv6/压力/填充仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1985 correct H1984 corrupted H1661 YAML at first parse boundary; source-only two pure orphan Defender regression tests are queued, not claimed run; no native network dispatch."}
```
