# PLAN029 H1688｜收回 H1687 当前源码真实 GUI/CLI 结果，保留双出口未验

- H1687 SOURCE `0d89843b6d2243945a81f45bb413be16ca7a97eb` [Windows Action 43240195695](https://github.com/lly8666/wbd-next/actions/runs/43240195695) **SUCCESS**。同一 GitHub SHA 实编 Rust cdylib、原 Go CLI、WinForms，并运行 GUI 保存/导入/重开及真实 Go `--check-config`。产物 [13954571876](https://github.com/lly8666/wbd-next/actions/runs/43240195695/artifacts/13954571876)，ZIP SHA256 `f707c9b6ecfe25b8d41d15e1354a6bfa4bd984a741f395a34b34cbff84f160ed`；Go SHA256 `813727ce184770be1895c6f24081045f04aeb640b5a312cd05c54e816eda7c9c`；Rust DLL SHA256 `6ddd97f5e5a6992177cf4f5f0f0f815a99866a85fe3f1c3a79c89bced693f3ac`。
- 真实配置读回覆盖服务器域名与 SNI 分离、外层1460/显式1500、内层Rust自动派生不回写、Normal/Game4、两个单DNS及老 `dns4` 首项迁移/备选弃用、重开保留。**SCOPED FUNCTIONAL_PASS 仅 GUI+CLI 配置**；Action receipt 明示签名 Wintun 业务、DNS两出口、no-WFP OS Applied、Direct TCP/UDP、flow padding 全部 NOT_RUN。不得把 GUI save/readback 写成应用网络成功。
- H1686 [Action43239063021](https://github.com/lly8666/wbd-next/actions/runs/43239063021) 缺相同SOURCE Rust DLL 的实测 FAIL 保留，不以成功结果改写。H1685 [Action43238034430](https://github.com/lly8666/wbd-next/actions/runs/43238034430) 原两OS native scene 已结束 SUCCESS，仍与 PLAN029 D1–D5/P1–P2 资格无关。
- Windows TCP 能力门 H1669/H1672 的真实 Wintun SYN→SYNACK 失败未解决；不能虚构 kernel feasibility PASS，也尚无确证可选择 Direct-only smoltcp。当前 Rust `v4_client_split.rs` 只有纯 classifier/flow-pin 单测，未接 Wintun 原 ingress。四阶段 no-WFP Win32 stage 仍 `assemblyOnly=true`；legacy exact-WFP migrator、route intent crash owned recovery、实际 Ready/Stop 待做。
- Next: 优先收敛真实 Windows 内核接入首个因果失败；独立补齐 no-WFP owned crash/legacy migration+Ready/Stop，随后按契约将 Rust ingress/DNS/FakeIP/Direct 双出口完整接线。无重复 Action、无新028矩阵/030、无产品 PASS 冒称。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback"],"reason":"H1687 same-source real WinForms and Go CLI config Action PASS on source-built Rust DLL; signed OS/DNS/Direct product remains NOT_RUN. H1686 real failure preserved."}
```
