# PLAN029 H1834｜H1833产品装配Go编译已恢复，验证真实WinForms保存/启动配置（非OS Applied）

- H1833 SOURCE `b43334885ab7fae468e896609e748294dc6ccc8b` [Action43587003652](https://github.com/lly8666/wbd-next/actions/runs/43587003652) 旧Go overlay精确装配、Windows Go主程序/测试、Windows/Linux Rust回归各自success；[Action43587003694](https://github.com/lly8666/wbd-next/actions/runs/43587003694) Windows H1661 DNS cold source编译/配置负测success；governance [43587003744](https://github.com/lly8666/wbd-next/actions/runs/43587003744) success。先前H1832三个因4项result_blob旧值导致装配FAIL的Action原样保留，不掩盖为业务PASS。以上均**NOT_SIGNED_REAL_NETWORK**。
- 下一闭环只在现有[WinForms按钮VM harness](r0/go_overlay/windows/gui/M0Plan028GUIButtonsVMHarness.cs)增加H1834具体断言：真实编译GUI字段含`split-enable` Bool（默认off）与`cn-rules-file`文件输入；在GUI切Normal/off，写入owned便携相对小域名表，实际`SetEditor→保存配置→PortableStore.Effective→子进程StartAsync` 的最终JSON含`true`及程序目录内绝对规则路径。Fake Session依然仅模拟GUI交互，绝不宣称签名驱动、OS Applied或真DNS。保留原M0按钮/Stop/Ready负测。
- H1834新SOURCE WinForms真实GUI编译/VM执行及生产OS起网在本次提交时均**NOT_RUN**。先收自动源锁GUI Action；只通过GUI字节与模拟session后，再单独安排一Action真实非CI GUI Connect/Stop、有效DNS/CN路由，不能将这次fake子进程PASS充作D5。需继续Game4 NativeSplitWorker/D4 IPv6/P1 P2低延迟/RSS/慢盘Stop，029仍IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Test-only Windows WinForms interaction harness verifies newly introduced portable CN split GUI fields travel to saved/effective next-session JSON; no production source or user-facing setting changes."}
```
