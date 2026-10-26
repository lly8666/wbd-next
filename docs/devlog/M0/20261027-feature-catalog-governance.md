# 2026-10-27 产品功能登记治理

用户直接授权补齐功能登记、正式/实验区分和分支位置；Governance 自动覆盖 main、work/**、experiment/**。
本工作使用独立 experiment/feature-catalog-governance-20261027，不接管 M0 或 FEC/Windows 产品任务。
初始审阅基线为 integration/w168-freeze-windows-adapter-20261026 的
6e271c1e01aefadb4266eed44646d51806f88d49。

新增 docs/features 唯一功能入口、结构化卡片和只读索引，沿用现有 devlog 的 feature-impact 声明。
registry 继续只管角色权限/语义归属；不创建第二套任务、审批或状态系统。
main/work 原有身份和范围门保持；实验分支仅运行功能目录门，不冒充正式工位。
用现有热读取预算替换旧历史索引入口，不增加第九个必读文件。

正式晋级与合并分开；平台、源码和测试范围分开。跨分支目录的发布是显式元数据同步，
不能假装某个实验分支未推送/未同步的功能已经自动进入 main 的目录。

本次功能库存明确 NOT_INITIALIZED；下一位 agent 按 docs/prompts/FEATURE_INVENTORY_INIT.md
一次性盘点当前分支，之后增量维护。产品没有改动，产品测试 NOT_RUN。
治理验证待本分支 Actions；失败与最终结果在此追加，不能用工具绿灯冒充产品 PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"本次只补产品功能登记/发现/声明检查与长期接班规则，未改变产品数据路径、配置默认或平台功能；已有功能的一次性盘点另行执行。"}
```
