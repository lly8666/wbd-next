# PLAN-005：完整模块工作包，减少M0逐步派单

用户指出M0自身仍在调优，其他工位若每开发一点就等M0集成/重新分配，会让并行流程串行化，并要求作出决策。核对main `02a69b2`、四个worker实际分支与现有分配；本次只修执行规则和过期串行文字，不替正在开发的M0改代码、不改worker cursor或伪造交付。

决定沿现有assigned_task一次授权完整模块能力，包内开发/Actions测试/修复/S→H自主推进；普通commit、H和局部PASS都不是等待集成的门。M0明确接口/路径与完成条件后继续调优，在安全批次边界或下一真实路径需要时集中集成，真实共享阻塞/硬门问题才提前处理。保留第一处必要接口接线，不把所有集成拖到产品末尾。

更新AGENTS/START/GOVERNANCE、M0–M4固定提示词、TEST_PLAN/实施顺序和两份旧决策；project和registry只替换M0的过期“024结束后才分配”说明，所有assigned_task、角色/分支/epoch/revision/allowed_paths保持不变。具体新工作包仍由当前M0结合活动文件一次登记，避免本聊天与它竞争分配；旧小任务完成不构成任意扩展到全模块的授权。未新增治理层、状态/schema、工作流或产品代码。

发布沿既有维护分支/PR，Actions维护回归检查结构、工作流和工具契约。产品/性能/物理本次NOT_RUN；不dispatch产品测试、不覆写其他工位事实。验收后在本日志记录精确来源和结果。

SOURCE `58dbcc50219aff7fb7726b7a3db2b2d5fa74cd88` 的 [Actions38996638150](https://github.com/lly8666/wbd-next/actions/runs/38996638150) attempt1 SUCCESS：169项治理回归、workflow语法、结构/资格账本及模型检查通过。下载核验artifact `12086744010`，ZIP SHA-256 `32e3425b50ba58691253ffe8f06427c55f3cfde642c480f0af43531ab393dcdf`；结构结果明确product/physical NOT_RUN。[PR9](https://github.com/lly8666/wbd-next/pull/9)只改变本次执行规则/提示词与说明，具体工作包登记仍由活动M0一次完成。
