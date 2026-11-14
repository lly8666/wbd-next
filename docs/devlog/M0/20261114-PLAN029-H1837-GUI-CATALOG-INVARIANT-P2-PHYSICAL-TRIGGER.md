# PLAN029 H1837｜一次修配置契约根因、一次触发真实P2机制鉴别

- H1835 SOURCE `dc26cdb` GUI [Action43587702812](https://github.com/lly8666/wbd-next/actions/runs/43587702812) 的Rust cdylib、原Go、真WinForms构建PASS，**WinForms真进程首次失败**是`PortableStore..ctor`报`GUI 参数清单与客户端不一致`。对照原Go精确assembly：`windows/gui/fields.json`有`split-enable`/`cn-rules-file`，但`docs/PARAMETERS.json`少两项，说明CLI/GUI/目录跨文件契约碎裂；原检查正确fail closed，不移除它。H1835真实GUI最终读回、OS起停均NOT_RUN。
- H1836 `8548fb1` 仅修改devlog和cursor，未命中`m0-wl-public-normal-full.yml`的`push.paths`；实际只有governance Action43587894507通过，**没有真实P2作业**，不能将“提交标记”报为一次性能实测，更不能报失败/成功。
- H1837把两个字段在原Go`docs/PARAMETERS.json`里精确补齐：`split-enable:Bool=false`、`cn-rules-file:String=""`，均作为`client-windows` JSON 参数；同一manifest新增严格补丁及新的`result_blob`。已在提交前从原始Go源码重放所有11+1项PARAMETERS补丁与现有30项GUI字段补丁，得到**59/59完全相同键**、两个类型/默认正确。未来`r0/go_overlay/assembly/assemble.py`所有文件提交前比较**最终装配产物**目录与GUI键，不一致时用missing/unknown key精确拒绝；不放宽manifest、权限、OS WAL或配置未知键的检查。
- H1837现有源锁H1663真WinForms→Go`--check-config`夹具新增显式CN规则缺失早拒绝，恢复正确文件后再完成Normal/游戏关闭开关的配置读回；不认为`check-config`或模拟Session是signed OS Ready。
- 为确定Direct 6.36s异常首个等待段，本提交**真正修改**`tools/m0_plan029_h1815_p2_real_mixed.py`（这次`push.paths`匹配），使用已授权的**唯一**`[plan029-v3-real-p2-rebuild]`标记，允许自动创建**同新SOURCE**签名Windows Npcap/Wintun + WSL2 Linux P2场景。除了原有物理与Direct 1MiB每16KiB sleep4ms、全程Tunnel小UDP/源码/Stop，增加物理/Direct分阶段耗时差、最差增加等待阶段和耗时比（只观察、不乱设性能通过阈值）。新SOURCE的任何P2值在此提交时仍**NOT_RUN**；不得重派H1836文档提交。
- 跨域真问题收敛优先级：配置目录和source-proof建立后，结合签名P2相位确定调度的真实瓶颈；FakeIP慢fsync并发Tunnel与Crash/Stop；Game4必须复用同Rust分流owner且有实际多lane实体；IPv6既有拒绝/捕获范围恢复；P1 CPU同VM因果归因。均OPEN，不退回028全矩阵或030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Repair original-Go exact portable GUI/CLI manifest parameter contract and enforce assembled-key equality before Windows startup; add P2 phase differential evidence source trigger, without new runtime protocol behavior."}
```
