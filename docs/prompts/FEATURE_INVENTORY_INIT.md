# 一次性功能目录初始化｜可交给全新 agent

你负责 `lly8666/wbd-next` 的当前功能盘点。先刷新远端，目标范围是
`integration/w168-freeze-windows-adapter-20261026`，用其最新精确 HEAD 作为本次审阅 SOURCE；
同时读取远端 main 的治理规则。先读 `AGENTS.md`、`PROJECT_CHARTER.md`、`START_HERE.md`、
`docs/features/README.md`、`docs/features/inventory.json` 和 `docs/handoff/CURRENT_INTEGRATION.md`。
若目标分支已被合并/替代，先按远端现有交接记录确认接替分支，留痕，不能凭日期猜测。

在独立工作目录从目标 HEAD 新开 `experiment/feature-inventory-init-<日期>`。
本任务只整理功能文档与必要的目录工具问题，不开发产品功能、不调参数、不重跑性能矩阵，
不修改其他工位权限/cursor。不要从默认分支旧快照覆盖当前集成分支，也不要合入整个集成分支到 main。

## 盘点方法

1. 先看现有目录，若已有部分条目就补齐，不重新发明一套文档体系。
   从 CLI/help、配置结构/示例、GUI 绑定、公共产品入口和近期精确 SOURCE 的证据反查实现；
   按相关模块读源码与近期 devlog，只有疑点才展开历史。不可用聊天记忆或仅有设计文档判定已实现。
2. 用稳定 ID 按产品能力归并，一项能力一张 `docs/features/entries/<id>.json`，
   避免每个函数/参数一张卡，也避免一张“所有网络功能”掩盖平台差异。
   检查范围至少包括：Normal/FEC off、fixed、auto、Game2/4 与错峰；
   外层重传/去重与首次交付；加密/硬件后端；MTU/分片/大包；连接建立/认证/多客户端；
   rotation、idle、keepalive、黑洞恢复；Windows/Linux/ARM 的实际接线；GUI/配置、DNS/分流/IPv6；
   portable、驱动、部署。这个清单是核查线索，不是声称这些功能均已完成。
3. 每项写清用途、当前默认值、CLI/配置键/GUI 入口、适用模式和平台、实现与使用说明链接、
   限制、真实开发分支与已存在代码的分支。没有 GUI/配置入口要如实写未接线或不适用原因。
   实验功能必须标 experimental，并核实所在分支；main 中存在也不自动 formal。
   formal 必须有 main 集成和明确采纳依据及适用产品证据。资料不足保守标实验/未验，说明缺口。
4. verification 按平台/模式拆分，保留精确 SOURCE 和现有 run/evidence 链接；
   BUILD_PASS、模块 PASS、产品功能 PASS、物理 PASS 不混用。
   旧源码证据保留其原 SHA，并写清与本次盘点源码的差异/未重验边界；不能把旧 PASS 改写成新 SOURCE。
   原 FAIL、NOT_RUN、容量限制都保留。已撤回的试验不登记为可用功能，可标 retired 并链接撤回原因。
5. 先盘当前目标分支；对相关实验分支只做有界核实，记录实际代码位置，不全仓库考古。
   尚未进入当前分支的代码用 `https://github.com/lly8666/wbd-next/blob/<精确SHA>/<路径>` 引用。
   文件中严禁凭据、私钥、真实业务内容或大原始抓包。

## 完成与边界

- 更新现有 devlog，记录审阅 SOURCE、方法、覆盖范围和未验项，加 feature-impact updated 声明，
  列出本次新增/更新条目 ID。中断发现遗漏先事实恢复，注明 recovered，不能编造历史开发意图。
- `inventory.json` 的 `inventory_source` 写审阅的产品 SHA，`scope_branch` 写真实目标分支，
  `baseline_source` 保留首次治理落地基线；`review_ref` 指本次盘点日志。
  信息不足就 PARTIAL 并列 gaps。范围均已盘点时可 COMPLETE_FOR_SCOPE；
  “功能已登记但测试未跑”不是目录缺项，仍 NOT_RUN，绝不因此升级产品资格。
- 当前M0在main维护目录，Governance检查结构/引用/声明；另获独立分支授权者遵守其授权。执行验证只在Actions。
  一次便宜检查覆盖整个目录，不为每张卡派发 Action，不跑无关产品矩阵。
- 独立分支的目录用PR合回main；M0直接main增量维护，无需重新开分支初始化。单独发布未集成实验目录时只提交文档元数据，
  未合入功能使用精确源码链接，available_on 不虚填 main；不得顺带合入实验产品代码。
  没有将目录发布到控制分支，就不能声称其他分支已经自动看到全部实验。
- 最终报告条目数、正式/实验/退役分类、真实未验/缺口、PR/Action 和长期入口。
  此后每次开发按同一目录增量维护，不再做第二套初始化或把全部历史塞进启动提示词。

项目主旨不变：真实业务首次到达优先，低延迟、无 HOL、低系统开销；保留必要完整性、
隔离、generation、固定密文重传与 MTU 等现行硬约束。盘点不是修改产品设计的授权。
