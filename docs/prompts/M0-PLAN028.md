# M0｜PLAN028接续提示词

你继续lly8666/wbd-next的PLAN028。**2026-11-03 用户已明确要求PLAN027A限定范围收口，未来另找全新agent开工028；本包尚未开始施工。**先核 [027A H998 用户接受范围收口证据](../evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json)：真实在线物理出口MTU从1500改1280后3/3小业务没有回应（FAIL），ARM64 Game4FEC真实业务/FEC/Stop可见但Actions失败，远端ICMP Type3/Code4未测，CPU优化因果未证。028§4.1–4.2 必须在实际新路径重认证/会话接管时补齐已知在线预算衔接，不假装027A已在同一连接热更新成功。先读START_HERE/AGENTS、M0长期提示词、最新registry/cursor，再读 `docs/decisions/M0-LEGACY-ROLLOUT-20261102.md` 和 `M0-PLAN028-SESSION-CONFIG-20261102.md`。默认上轮可能中断，只追checkpoint增量，先收在途Actions不重复派发。

本提示词由用户实际调用或既有完整序列授权推进时启动本包；仓库仅存在文件不等于已开工。PLAN027已限定范围收口，先核PLAN027A交付及本包实际依赖，不因历史NOT_RUN重开027，不复制第二套恢复器，不将旧PASS推广。用既有registry/cursor登记本包，不添加审批/任务系统。

2026-11-02新增前置：027后先做PLAN027A统一MTU，再到本包；读取其交付摘要与docs/architecture/MTU_CONTRACT.md，直接复用预算/OS读回，不另写公式。若用户启动完整序列，按此顺序连续推进。

MTU配置只有外层完整IPv4 IP上限（**以后普通默认固定1460B、不含L2；1500B仅为显式最大值，不是默认**）；client传意图，server按自身实际限制收窄，内层自动算/应用/读回。不要要求两端手填内层MTU，不把派生结果回写为用户外层值或覆盖其他client的TUN。

目标：账号密码操作简化、自动/手动IP、同账号多设备、一个服务端口、每client独立配置接入既有数据面。先定最小配置/session/endpoint/snapshot接口，再连续写齐双方与调用方；029 DNS、030 CLI独立模块可并行，main共享接口单写入。

重点真实证明七模式换laneA→A+B→B、同账号不串身份/IP/配置、Game健康lane不中断；复用老15s Health/90s dead/1–30s退避和当前修复，别重做FEC/重传/密码算法。route-key自动化若有握手前依赖要解决，不隐藏手工key要求或关闭认证。

网络切换按028§4.1–4.2现在做公共会话接管和Windows/Linux原生通知，不等Android，也不提前造安卓客户端。系统事件合并约200ms/最长500ms，不等dead90就尝试新路径TLS认证；保留合法session/IP、更新lane密钥/generation和raw/Npcap出口、重新计算MTU与auto启动状态。能重叠就交接，已断就直接恢复；Game有可用lane先送。休眠切网不唤醒、用户Stop不复活，旧建链/回收不能覆盖新会话。默认外层1460不改。过滤自身TUN/路由通知避免重连风暴，不加周期探针/逐包FFI。

复用七模式场景补真实出口切换，Normal auto/Game4最高档补重叠与先断后连、MTU变小；同账号另一设备要持续工作。分别报告通知到建链、认证到首包时间及CPU/p99，500ms仅通知处理预算不是高延迟握手总SLA。Android网络回调/底层绑定/VPN旁路与真机测试明确留到Android阶段；当前桌面资格不能冒充Android PASS。

先算、读实现、再改，聪明自主处理普通决策；遇问题抓最窄证据，必要修正方案并说明，别机械守旧、堆防御框架或刷seed。构建一次核SOURCE/hash复用，一Action一场景，不同场景并行，同VM比较顺序。低损换lane不能重置内层TCP，高损允许合理损失与重试，不追零丢小数点。

按包批量留短devlog/功能卡/证据，更新cursor。全包完成才报完成；单步结束自动继续，真阻塞推进独立部分。若用户仅启动本包，完成后交付并指出029/030入口；若整序列已授权，自动接下一已授权包。没有新任务时不扩测。
