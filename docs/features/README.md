# 产品功能唯一入口

本目录回答：有什么、怎么用、默认值、在哪个分支、哪些平台测过。
`.governance/registry.json` 仍管工位权限/语义归属；这里不派任务、不授予写权限。

先读 [inventory.json](inventory.json) 的完整性。NOT_INITIALIZED/PARTIAL 不是没有功能；
COMPLETE_FOR_SCOPE 仅表示指定 SOURCE 已盘点，不表示全部功能/平台 PASS。

接手运行 `python tools/feature_catalog.py list` 获取简表，或 `list --query fec`，按任务读卡片。
这是只读文档命令，不执行测试。GitHub 可直接读 [entries/](entries/)；Actions 会上传生成索引。
不全量读历史，不再维护第二份手写总表。

- 新功能先在 `experiment/<topic>` 登记 experimental；work 继续既有模块任务，integration 用于隔离集成。
- 一项产品能力一个稳定 ID。配置/默认值/平台接线/行为变化同步卡片、适用 CLI/配置/GUI/帮助与证据。
- 卡片记录研发来源 `development_branch` 和代码实际所在 `available_on`，不把计划合并写成已存在。
- main 合并不自动正式化。formal 另需 main 集成、采纳决定、精确源码及适用产品证据；退出标 retired。
- 实验尚未合入时，单独把目录元数据发布到控制分支，其他分支才会知道；用精确源码链接引用未合入代码。
- 每次交付在现有 devlog 写 feature-impact。纯内部优化可声明 none 并解释；中断先补事实，不用 none 掩盖参数变化。

格式、例子与边界按需读 [RULES.md](RULES.md)，复制 [模板](entry.example.json)。
Governance 自动范围是 main、work/**、experiment/**。目录门检查格式/引用/变更声明；
无法自动理解所有新功能，语义完整性仍由开发者及集成者审核，也不等于产品 PASS。
工位登记权限随完整工作包一次配置，不逐参数审批。

首次初始化交给新 agent 使用 [固定提示词](../prompts/FEATURE_INVENTORY_INIT.md)。
