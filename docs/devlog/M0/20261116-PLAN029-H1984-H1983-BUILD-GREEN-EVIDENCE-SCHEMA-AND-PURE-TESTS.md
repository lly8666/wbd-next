# PLAN029 H1984｜收 H1983 构建真实结果并修治理evidence格式

- [H1983 M0 Action43825343465](https://github.com/lly8666/wbd-next/actions/runs/43825343465) 原SOURCE `57b2fe47e71555538294370065f130b47c152b1b`：cheap装配 133157753633、Linux Rust133157987997、Windows Go133157988026、Windows Rust133157988038 全 SUCCESS，原生产品联网SKIPPED/NOT_RUN。[H1661 Windows Action43825343422](https://github.com/lly8666/wbd-next/actions/runs/43825343422) SUCCESS：真Win2025新 `TestPlan029NoWFPAssemblyRejectsUnreconciledDefenderSidecar` PASS；精确owned Defender COM Add/readback/CAS删除PASS（非TCP业务/完整D5）。
- [H1983原治理Action43825343455](https://github.com/lly8666/wbd-next/actions/runs/43825343455) 两job均 **FAIL**，原独立121单测PASS但结构验证FAIL。原artifact `structure.json` 第一异常 `evidence is for a different SOURCE`：H1983 evidence真实 `tested_source_sha=3d0d020...` 与 cursor一致，却缺规范 `source_sha`。H1984只补 `source_sha` 字段，保留原各失败状态，不冒充绿。
- 既有两个纯 Win32 Go `TestPLAN010NativeReadOnlyDiskStatusAndConflict`、`TestPLAN010OriginalNativeRecoveryNoShellOrLegacyFallback` 在H1983只编译、未执行。H1984只扩展原H1661 Windows-Go单场脚本的 `-run` 精确正则，覆盖这两个临时文件夹孤儿Defender侧证断言；不做额外 native TCP/UDP dispatch、不扩规则作用域、不允许旧 guard。
- 新 SOURCE 的CI/实网 **NOT_RUN**；本次不取代 H1978原native FAIL、H1974五次61ms卡顿，GUI真按钮、Game4 CN、IPv6/D1–D5/P1–P2/64MiB压力和padding仍 OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1984 add canonical H1983 evidence SOURCE and source-lock two existing pure orphan Defender read-only and recovery regressions in H1661 Windows Go job, original failures retained."}
```
