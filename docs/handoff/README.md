# 项目接班热索引（只作导航，不存第二份任务状态）

**更新时间 2026-10-26**：本页仅定位文件，数据读取优先级始终为：用户最新明确指令 → main 的 `.governance/registry.json` → 相应角色/工作分支 `cursor.json` → exact SOURCE 的 Actions 和 evidence。不要从该页推断 PASS，也不要仅凭实验的 `merge_ready=false` 否定本轮用户授权的隔离集成。

1. **20秒开始**：`START_HERE.md` → [当前跨分支热摘要](CURRENT_INTEGRATION.md)；需要权限再读 `AGENTS.md`、main registry 与指定 cursor。不要默认读所有旧日志。
2. **现行集成**：冻结 `freeze/fec-linux-w168-20261026` → [Draft PR #28](https://github.com/lly8666/wbd-next/pull/28)（基于 Windows 功能测试分支）→ [Draft PR #27](https://github.com/lly8666/wbd-next/pull/27)（日后 main 晋级）。精确两亲合并及语义差异见 [集成合同](../integration/M0-W168-FROZEN-ARCH-WINDOWS-ADAPTER-STAGED-INTEGRATION-20261026.md)，只在需要解决冲突时阅读全文。
3. **模块设计**：[架构入口](../architecture/README.md)、[模块导航](../architecture/modules/README.md)、[测试规则](../architecture/TEST_PLAN.md)。查看与任务相关的一两个模块，勿全量加载。
4. **保留历史**：[历史总索引](../history/INDEX.md) → [W168/Windows 日期与证据索引](../history/2026-10-26-W168-WINDOWS-INTEGRATION-INDEX.md)；旧热概览的原始快照保留于 [2026-10-26 合并前](../history/handoff/2026-10-26-pre-W168/README.md)。开发日记仍按 `docs/devlog/<工位或主题>/` 原路径；实验所有原始失败、机器收据仍在 `docs/evidence/fec-network-work/`，M0 实际失败仍在 `docs/evidence/M0/`，不移动、不改名、不删除。

**状态红线**：W168 Linux 双架构56个观察样本 ≠ Windows 七模式 PASS；当前已被旧 SOURCE Actions 真实验证的 Windows Normal/off TCP+UDP+Stop ≠ 新合并源码已通过；Windows M2 1536 + M1 2048 是候选配置不是性能资格；旧高压 +103B/AMD64 250Mbps INCONCLUSIVE 必须继续能检索。主线 `main` 未晋级前当前主线 cursor 仍为历史 H274。
