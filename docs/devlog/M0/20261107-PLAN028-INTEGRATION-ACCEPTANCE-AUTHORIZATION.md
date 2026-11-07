# PLAN028｜功能冻结与专项验收授权同步

用户2026-11-07授权将028收尾方法、验收和M0提示词统一；本提交仅改文档/任务范围元数据，不改产品、不派发Actions、不宣布新的产品PASS。

- 新增 `docs/testing/PLAN028_INTEGRATION_ACCEPTANCE.md`：跨层就绪/交接/MTU/退出契约，PPS/BDP/FEC/队列/CPU账本，按最早异常定位，未触发候选不得领修复功劳；L0短复现→L1广覆盖→L2渐进压力/弱网/恢复→L3有限综合长测。
- M0可依据理论和实测宿主/线程容量自主调整实现、参数、场景和合理性能容差，需先记依据并保留原结果；硬门不降。允许小错误当批纠正，不增防御框架，不刷seed、反复审计或穷举矩阵。容量不足停更重同族，不能把产品单线程瓶颈当坏VM免责。
- 同步028原计划、总览、START_HERE及两个提示词；移除已过时H号施工口令，纠正“同NIC/IP的MTU变化可忽略”。现行新代重认证资格不改写H998同socket热收窄失败。
- registry保留任务身份，只更新长期目标/完成条件；cursor只更新完成条件和一个context索引，保留M0当前SOURCE、sequence、下一步、在途实验、失败和所有证据。028仍IN_PROGRESS；029/030不能借本次授权自动启动。
- 检查范围：文档链接、JSON、治理/功能登记结构与差异检查；具体结果见本提交完成说明。不运行产品性能测试，不伪造功能卡资格。

```feature-impact
{"kind":"none","ids":[],"reason":"Docs-only acceptance methodology and existing M0 task/prompt alignment; no product/config/wire behavior changed."}
```
