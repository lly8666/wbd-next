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

首轮 SOURCE d21efa01e4ba32fa94b6b0e0b391978430ee3f5d：
- Governance 40363215456 的 Feature catalog PASS；实验分支原角色身份 job 按设计 SKIPPED。
- 完整 maintenance 40363215257 FAIL（223 tests）：新增必读目录导致 M0 热读取 34287B，
  超过既有 32768B。这是本改动的问题，缩短必读 README、把细则移到按需 RULES，不提高预算。
- 另外两条 frozen manifest 子断言在 fec_v2_policy.go / fec_v2_policy_test.go 失败。
  这两份文件从基线 6e271c1e 到本次 SOURCE 无差异；其修改来自原 FEC 分支的
  946346bb / 3b89a140，旧 Windows assembly/manifest 仍固定旧 blob。
  不修改这两份产品文件/冻结证据来冒充治理通过，留给现行集成任务核实。产品资格不受本次声明升级。

用户最新要求：本次只合入最新 integration/w168-freeze-windows-adapter-20261026，
main 暂不修改。后续随该分支合并继承治理工作流；旧分支未同步新文件前不声称自动覆盖。

最终工具 SOURCE 5dd2ac3f20f44b58f3d5b0568bad9a1df57aa4cc：
- [Governance 40368000934](https://github.com/lly8666/wbd-next/actions/runs/40368000934)
  Feature catalog、19项目录/原治理定向测试、workflow语法和仓库结构检查 PASS；原工位 job 在实验分支 SKIPPED。
- [Maintenance 40368000850](https://github.com/lly8666/wbd-next/actions/runs/40368000850)
  执行224项测试，热读取预算问题已修复，剩余仅旧 frozen manifest 的上述两条子断言失败。
  maintenance 整体保持 FAIL，不删除断言、不改冻结产品文件、不宣称全回归通过。
- 只改治理代码、测试和文档。目录工具代码已验证；产品功能盘点仍 NOT_INITIALIZED，产品/物理测试 NOT_RUN。
  结构化留痕见 docs/evidence/feature-catalog-governance-20261027.json。
- PR #29 目标是用户指定最新集成分支，保留其并行 Windows 产品提交；main 保持原样。

```feature-impact
{"kind":"none","ids":[],"reason":"本次只补产品功能登记/发现/声明检查与长期接班规则，未改变产品数据路径、配置默认或平台功能；已有功能的一次性盘点另行执行。"}
```
