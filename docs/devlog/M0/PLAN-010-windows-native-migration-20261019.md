# PLAN-010 老项目去PowerShell定向迁移审查

用户要求核对老项目后续去脚本内容并规划移植与临时工位任务。此次只在独立规划分支写方案，不改活动M0/M4源码、registry/cursor，不给其他聊天发消息，不部署机器。

审查wbd-next main 0613077c0858110adca21c02d16d72ac504c8775；M0 H178正在真实产品接线，M4 H26修Windows GUI进程等待。旧仓库固定a7a82db31fe736ffedee330795a3234d358f1984，刷新donor到6ec6b5836c2b70a85f2ef89c2f5ea4525c6ed340。diff核internal/windowsclient只有12文件（6产品/6测试、4新增），go.mod/go.sum无差异；逐文件blob在本证据JSON。没有导入旧治理/STATUS的巨大历史。

关键发现：基线已含大部分原生API/WAL，后续增量主要PnP指纹、ghost DNS有限恢复和lease只读审计。最新老版CLI/GUI仍执行PowerShell；native组装仍assemblyOnly，生产WFP Arm仍拒绝。donor最后N4/N5的有限PASS不能证明普通产品完整去脚本；完整ghost MTU恢复UNSUPPORTED、真实WFP/路由接管仍未验。本次读取源码和donor日志，未下载旧所有Actions产物复验。

PLAN-010选择固定基线+小增量+现有Go冷层真实接线，不改Rust数据面，不新增驱动，不整库升级。运行时Apply/Stop/Recover去shell，开发/构建/Actions脚本保留。M4主做，M0一次给路径与CI/Stop接口并集成；M1仅真实契约缺口才修，M2/M3无新任务。先结算015在途GUI修复，之后登记临时016，不强行将未完项目标完成。

测试复用旧Windows原生断言和新产品装配夹具，功能批量、性能按需同机单场景。全局网络变更必须有真实隔离；没有则报告NOT_RUN，不刷特殊ghost案例、不删除硬门。性能收益主要是连接/恢复时进程开销与可靠性，未宣称稳态加速。官方API文档仅用于最低OS与WFP条件边界，链接见决策文件。

本补丁仅方案、迁移入口和精确差异证据；临时任务尚待M0登记，产品移植/测试/物理均未由此完成。maintenance只验方案相关治理回归。
