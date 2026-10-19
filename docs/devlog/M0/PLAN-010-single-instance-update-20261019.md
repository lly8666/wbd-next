# PLAN-010 小更新：单代理环境，全包由M4完成

用户明确要求：M4完成全部去PowerShell工作，M0赋予最新Actions测试能力；开发按一台电脑只运行一个网络代理相关实例，不再为极端工况扩展。此授权覆盖上一版计划中的多代理/多Wintun共存前置。

已调整PLAN-010与MIGRATION：运行时连接/停止/恢复、GUI/配置/portable和脚本引用清除由M4整包完成；构建/CI脚本可保留。产品以现有实例锁和基本预检落实单实例，重复启动明确拒绝；不做多代理仲裁、第三方篡改/极端PnP自愈。正常系统API失败、取消、清理和一般重启恢复仍验，旧极端失败如实保留但不阻止正常范围收口。Actions管理网络保护只作为测试环境边界，不扩大产品要求。

核main fff6d04：公共worker入口仍仅允许M1/M3，M4产品workflow只有push/workflow_run，没有手动dispatch。因此要求M0一次补现有M4 workflow手动入口或公共M4 adapter，提供精确SOURCE/request/control与真实验证示例；M4自主触发/读产物/修复复测，不重复代跑或用无关push蹭CI。

仅更新待合并PR #15的方案；未改活动registry/cursor/产品/入口实现，不代宣称已授予实际Actions能力。M0合并后登记执行。
