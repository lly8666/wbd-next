# PLAN-008 集成解堵审查

2026-10-19按用户要求用精确远端main、五工位cursor、既有证据及Actions核进度。main 57fa576/M0 H167；最新SOURCE708ecd3的39176419445 API SUCCESS/已有证据14job PASS，不能当产品资格。

确认堵点：原GUI/CLI源码不在本仓库热树，但固定旧SOURCE已可访问，现有CI也已经使用；真正缺的是产品装配/入口接线与分工，不是要重新批准复用旧冷层。M0独占所有实际配置/UI写入造成M4无法推进。方案改为固定旧源+显式overlay清单，由M0一次授予M4适配文件；M0仍管可信认证、Rust运行时、能力门与最终集成。

M1当前c80ff6a的旧Governance39086314217仍红，日志确认继承历史边界；中央39095544653/M1 job117581114004对相同SOURCE已PASS。重新下载artifact12124433196验SHA256并读取receipt，无猜测。该run整体红属于M4，不能覆盖也不能让M1一直等。M3已有main scoped接受证据，恢复时消费，不重刷。

完整安排在docs/decisions/M0-integration-unblock-2026-10-19.md：M4产品shell，M2成熟质量契约，M1 Game去重/索引，M3恢复工作区；M0继续实际off/反向receipt/组合。后置Arc池化、RACK索引与小包优先。性能独立Action，同VM顺序旧新；功能可批量，编译产物复用，禁止每次小接线重刷14job。

本补丁只改方案/固定职责提示/入口与精确证据；未改产品、registry或worker cursor，未发消息/启动工位/部署物理。由M0合入并一次登记生效，避免抢写正在使用的主线和worker分支。

用户进一步要求五工位提示词长期通用，任务另行发布。已把五份提示词收敛到远端发现/恢复、稳定职责和交付纪律，去掉固定分支、FEC常量和本轮任务链接；沿用registry assigned_task+goal决策路径+done_when发布，cursor/evidence记录执行，不新增数据库或检查器。START_HERE和GOVERNANCE明确新包只需一次登记，用户无需反复换提示词。本轮任务摘要放在决策第6节，不是长期入口。
