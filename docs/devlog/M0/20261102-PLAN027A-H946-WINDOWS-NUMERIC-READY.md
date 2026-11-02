# PLAN027A H946｜Windows cold numeric OS MTU在READY之前核验

恢复main `f09395c4d38e59da8789b8d4e275a45d8691a901`，H943 六项实原生SOURCE `ae3e7e9f52c415b60d596b7e923ade07f463d4ed`已收，不重复派发。功能层剩余的Windows numeric readback缺口由原有 `N4RealWindowsProduct.RuntimeMTU`/五阶段WAL + 实际OS Inspect解决：产品在发布 READY 之前调用一次冷只读数值检查并核实 planned inner，相同generation/原owned Stage，不向Go新增MTU计算、不碰健康稳态数据路径。验过后打印有界数值回执；CLI默认outer仍1460，不把inner当outer。

真实Windows↔WSL2夹具只在新default1460/explicit1500选择要求该数值标记，与当前真实外层配置匹配并纳入report，不从CLI制造一个“已读回”的inner。加纯解析负例覆盖missing/duplicate/不等/范围。历史legacy1400模式不用新门追溯改PASS。源冻结后再运行相应一次构建和原生验证；当前全部新SOURCE **BUILD NOT_RUN / NATIVE NOT_RUN**，不能从H943老PASS推断。DF0/DF1与Game4 3Mbps未动。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"One existing real Windows WAL/OS numeric Wintun inner-MTU receipt is now checked before READY and captured by source-locked native harness; current code untested, existing H943 evidence preserved."}
```
