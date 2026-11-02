# M0｜PLAN028接续提示词

你继续lly8666/wbd-next的PLAN028。先读START_HERE/AGENTS、M0长期提示词、最新registry/cursor，再读 `docs/decisions/M0-LEGACY-ROLLOUT-20261102.md` 和 `M0-PLAN028-SESSION-CONFIG-20261102.md`。默认上轮可能中断，只追checkpoint增量，先收在途Actions不重复派发。

本提示词由用户实际调用后启动本包；仓库仅存在文件不等于已开工。先核PLAN027真实完成/相关开放缺陷；未完成且仍影响依赖的部分沿原任务解决，不复制第二套恢复器，不将旧PASS推广。用既有registry/cursor登记本包，不添加审批/任务系统。

目标：账号密码操作简化、自动/手动IP、同账号多设备、一个服务端口、每client独立配置接入既有数据面。先定最小配置/session/endpoint/snapshot接口，再连续写齐双方与调用方；029 DNS、030 CLI独立模块可并行，main共享接口单写入。

重点真实证明七模式换laneA→A+B→B、同账号不串身份/IP/配置、Game健康lane不中断；复用老15s Health/90s dead/1–30s退避和当前修复，别重做FEC/重传/密码算法。route-key自动化若有握手前依赖要解决，不隐藏手工key要求或关闭认证。

先算、读实现、再改，聪明自主处理普通决策；遇问题抓最窄证据，必要修正方案并说明，别机械守旧、堆防御框架或刷seed。构建一次核SOURCE/hash复用，一Action一场景，不同场景并行，同VM比较顺序。低损换lane不能重置内层TCP，高损允许合理损失与重试，不追零丢小数点。

按包批量留短devlog/功能卡/证据，更新cursor。全包完成才报完成；单步结束自动继续，真阻塞推进独立部分。若用户仅启动本包，完成后交付并指出029/030入口；若整序列已授权，自动接下一已授权包。没有新任务时不扩测。
