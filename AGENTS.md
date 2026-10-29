# WBD Next｜全体agent硬约束

1. 用户最新指令优先。真实业务首到、低延迟/无跨流HOL、低CPU；允许有界内存。认证/完整性、账户和lane隔离、generation、原密文、MTU、真实驱动结果、owned Stop不可退让，见PROJECT_CHARTER。
2. M0在main连续开发；只有另授独立任务用其他分支。新聊天或定时提示默认上次可能中断，按START_HERE恢复main/cursor后增量与在途Actions，不重复dispatch、重扫历史或复活已结束FEC工位。
3. 当前用户授权优先级为PLAN027：先去线上M2 Receipt及热依赖、接老版低频质量/Health与机会重传，简化验证后再补接线、跑矩阵、优化。唯一细则见docs/decisions/M0-PLAN027-LOW-RATE-FEEDBACK-CLOSEOUT-20261030.md；旧PLAN026/cursor next_action冲突处被覆盖，历史证据不删。
4. Go保留成熟TLS/OS/GUI冷控制，Rust稳态，禁止Go逐包FFI/空轮询/双控制器。普通实现选择自主做，不增防御性包装/通用框架，不为假设极端钻牛角尖；必要正确性检查保持。
5. 同一批代码/双方调用/配置读回/功能卡/夹具先齐再冻结SOURCE。执行测试在Actions：一Action一场景测试控制进程/测量job，必要双端进程允许；不同场景可独立Action并行，同VM A/B顺序。一次构建按SOURCE/manifest/hash复用；容量耗尽停更重同族，不刷seed，产品锁/单核瓶颈不能伪称环境。
6. 单main写入，不覆盖未知变更、不reset/force。每批短devlog带feature-impact，功能卡统一记录；阶段/恢复更新cursor与在途run。旧SOURCE PASS不转移新SOURCE，失败/未验/物理范围保留。
7. 满足当前完成条件即交付。定时器重复提示在无新实质任务时只回复基本完成待验收，不重新开发或跑矩阵。凭据/正文/大pcap不入库，清理自有大文件，不擅自部署物理机或发其他聊天消息。

历史细节按需读docs/GOVERNANCE.md、docs/history/2026-10-28-M0-MAIN-HANDOFF.md及原证据。
