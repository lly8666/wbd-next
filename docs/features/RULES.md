# 产品功能唯一入口

这里回答“有什么、怎么用、默认是什么、在哪个分支、哪些平台测过”。
`.governance/registry.json` 仍是**工位权限/语义归属**唯一权威；本目录不派任务、不授予代码写权限。

**当前完整性先读 [inventory.json](inventory.json)**。`NOT_INITIALIZED/PARTIAL` 不是“没有功能”；
`COMPLETE_FOR_SCOPE` 仅表示指定源码范围已盘点，绝不表示所有功能/平台 PASS。

新 agent 每次接手：读取本页、运行 `python tools/feature_catalog.py list` 获取简表，再按任务读条目。
该命令只是本地读取文档，不执行产品或测试；可用 `--query fec` 缩小范围。
在 GitHub 上可直接查看 [entries/](entries/)。CI 上传同源生成的索引，不另维护一份手写总表。
历史日志仍按问题查找，不把全部开发历史塞进接班上下文。

## 登记与晋级

- 新功能/新行为试验从明确基线开 `experiment/<topic>`；先登记 experimental、真实开发分支与 NOT_RUN。
  `work/**` 继续既有授权模块任务，`integration/**` 只做隔离集成；不以临时分支绕开实验登记。
- 一项产品能力一份 `entries/<stable-id>.json`；修复、优化、调默认值更新原条目，不为每个 helper 建卡。
  多分支同能力沿用同一 ID，集成时合并变化，不能靠换 ID 丢掉历史状态。
- `development_branch` 指研发来源；`available_on` 只列已有代码的分支，不列“准备合并”的目标。
  实验可能已进入集成分支甚至 main，仍保持 experimental，直到明确晋级。
- formal 需要实际 main 集成、精确 SOURCE、明确采纳决定和适用产品功能证据。
  模块/编译 PASS 不能单独晋级；Linux PASS 不推广成 Windows PASS。正式功能也可以有未验证平台。
- 退出的功能标 retired，保留原因和替代入口，不直接删卡。历史首次盘点无法使用 experiment 命名时，
  如实填写旧分支及 `legacy_branch_reason`；此例外不用于未来新开发。
- 跨分支发现：先刷新 main 和自己的实际分支。目录描述其提交时的已知位置，不能假装实时全仓库数据库；
  新实验尚未集成时，要把其简短登记条目同步给集成者/控制分支（不带产品代码），其他分支才会知道。
  `available_on` 中仍只写代码实际存在的位置。没有这次发布，不能声称其他分支自动知晓。
  仅同步卡片时，尚未并入当前分支的代码/说明使用本仓库 `blob/<40位SOURCE>/<路径>` 永久链接，
  不能为通过引用检查而提前合入实验代码；开发者负责核实链接内容。

## 条目格式

复制 [entry.example.json](entry.example.json) 到 `entries/<id>.json` 后据源码填写。
必填：用途、责任归属、正式/实验/退役、开发及可用分支、配置/CLI/GUI入口或不适用原因、默认值、
实现/说明路径、按平台和模式划分的验证状态、限制。PASS/FAIL/容量限制要有40位源码和证据。
示例不是有效产品登记，不能照抄其中的假源码或占位说明来通过检查。
尚未实现的预登记使用全 PLANNED 验证项、available_on=[]、code_refs=[]，并引用现有设计说明；
不能为了登记把未实现功能写成可用。退役功能可以 available_on=[]，保留历史源码链接和退出原因。

**登记必须伴随本次交付：** 新增/删除功能、模式/平台接线、参数/默认值/限制变化，修改对应卡片，
在既有 devlog 加一个小声明（不另建提交日志系统）：

```feature-impact
{"kind":"updated","ids":["example-feature"],"reason":"说明实际改变了哪项产品行为和哪些入口。"}
```

纯内部优化或无功能变化的修复可以：

```feature-impact
{"kind":"none","ids":[],"reason":"例如仅减少临时内存复制，配置、默认值、平台和功能语义均未改变。"}
```

必须是真实解释，不能用 none 掩盖新增参数。中断恢复时先补遗漏登记，注明 recovered 和事实依据。
工位需要登记目录写权限时，由集成者随完整工作包一次配置，不能让每个功能等待逐次审批；
用户明确授权的实验任务按其范围执行。本目录不扩大任何 worker 的产品代码权限。

## 检查范围和维护

Governance 的 `Feature catalog` job 在 main、work/**、experiment/** push 时检查：条目格式、
引用存在、正式晋级字段、产品代码变化是否有 devlog 声明、声明的卡片是否实际更新。
它不会自动读懂任意新算法，也不能证明功能说明完整或网上证据真实；这些仍需开发者和集成者审核。
原角色身份/路径审计继续用于 main/work，实验目录检查通过不等于获取 M0–M4 权限或产品 PASS。
治理工具/规则改变时，同范围的 maintenance workflow 另跑完整治理回归；普通卡片更新不触发完整回归。
integration/** 按用户要求不加入自动触发，可从实验分支的同源候选先验收，集成后手动核所改内容。

卡片只保留当前语义和关键证据链接；旧细节留在 Git/devlog。阶段收口更新原卡，避免总表、卡片和日志三份手工状态。
首次初始化任务见 [固定提示词](../prompts/FEATURE_INVENTORY_INIT.md)。
