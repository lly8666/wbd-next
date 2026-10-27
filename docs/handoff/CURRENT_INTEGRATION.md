# W168 / Windows 当前热摘要

权威仍是远端main registry、M0 cursor及精确SOURCE Actions。本页是索引，不另管进度；读者须先刷新远端。历史细节按问题查 [原集成历史](../history/2026-10-26-W168-WINDOWS-INTEGRATION-INDEX.md)。

## 已完成集成，资格分开

2026-10-27 用户授权完整开发分支合入并覆盖main开发树；f6469a之后修复治理/装配，审阅点main为c7fef14b、M0 H291。不能再按旧快照声称“main未合入/仅Normal接通”。开发树集成完成不等于正式产品完成。

- 4977f12 / [40449519463](https://github.com/lly8666/wbd-next/actions/runs/40449519463)：七模式初始真实Windows↔Linux功能；Auto启动档通过不代表自然调档。
- a0c8eeb / [40457048399](https://github.com/lly8666/wbd-next/actions/runs/40457048399)：操作者revision2正例，范围与自然质量控制不同。
- 9d2362d / [40476182202](https://github.com/lly8666/wbd-next/actions/runs/40476182202)：自然Auto真实FAIL，M2控制TX序号差428B，未完成自然变档与完整Stop。已在本轮审计独立核验ZIP/hash及日志，根因仍待定位。
- 6d35857 / [40483279229](https://github.com/lly8666/wbd-next/actions/runs/40483279229)：receipt四项FAIL，其他kernel/FEC/normal/engine范围成功。旧公开CLI/组合流程另有装配红灯，不能混成产品恢复失败或直接删除。
- b305e29的Governance/maintenance/G2成功只是治理结果。Windows [40483279255](https://github.com/lly8666/wbd-next/actions/runs/40483279255) 已追到最终FAIL并核artifact/hash：Fixed和Auto启动PASS；Normal在WL-N0 seal拒绝退出（NPF drop7333），四个Game模式FAIL，最后Game发送器报WinError10051。不能把旧七模式短贯通当本轮压力PASS。

## 最新授权整改入口

[完整施工与极限验收方案](../decisions/M0-WINDOWS-EXTREME-REMEDIATION-20261027.md)；[证据与资源摘要](../evidence/windows-main-audit-20261027.json)；[给运行中M0的提示词](../prompts/M0_WINDOWS_REMEDIATION_EXECUTION.md)。

主要缺口：Windows仍由Go逐包搬运/查身份/调FFI；1536 shadow还会阻塞新业务；FEC take后分配失败丢失状态；旧TCP缺口跨半序号空间可能误拒新包；Game1200B上限/坏lane组级失败；Auto长期元数据容量和清理锁；repair比例外还有过小绝对帽。CPU的Go EXE包含Rust DLL和内核调用，不能按进程名归因。

用户本轮要求先完成全部整改代码、测试用例、装配清单与夹具，再冻结SOURCE统一跑Actions；功能合批、性能一Action一场景、同机AB，容量不足停止更重测试。保留身份/完整性/generation/同密文/owned Stop硬门，不恢复旧快速重传目标。

历史WL-N0失败、自然Auto、完整Auto曲线、全局GUI/WFP/DNS/IPv6、生命周期、物理和历史80s等分别按证据处理，不用新正例覆盖。单公共端口/认证租约等下一批旧功能恢复另行实现；现有WindowsGame仍使用ServerPort+i，未宣称该目标完成。
