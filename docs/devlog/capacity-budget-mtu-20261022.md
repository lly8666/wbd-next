# 极限参数闭环与自动内层MTU

2026-10-23，用户直接授权；基于 main d8ba2cf2，独立分支 fix/capacity-budget-mtu-20261022。先核原测试工位的 S030/S031，不覆盖其 status/cursor，不重复压力请求。S030 每端约7k输入被 record1180→FEC source1135 拒绝；c297a805 的固定1280修复是根因依据，按用户最新要求改为外层配置自动推导内层TUN，不能停留在更换固定常量。

代码：Linux CLI --outer-mtu 默认1500；取接口MTU、MSS、双端已认证record limits的共同约束，扣record31/FEC14/Game16；建链后、Rust读取TUN前应用。Auto保留FEC空间，所有lane只收紧共有TUN。无需逐包计算/新wire字段；保留现有Rust path/DF硬门。Windows另一入口由M0并行维护，本次只给统一迁移语义，不宣称已接线。

测试：Actions构建原Go+Rust ARM包、Go预算反例；同包九个便宜功能组合（Normal/Fixed/Auto×1280/1500、双端不同配置、Game2/4），读取实际MTU后验边界与超限DF及Stop。这是功能批次，不是性能比较。独立 network-harness-check 跑模型及夹具合同；性能压力继续由原测试工位自己的单场景Actions推进。

模型与方案：tools/network_harness/envelope.py 复用 cost_model，区分外层/内层、包数权重、partial FEC、Game复制、保留缓存与短发送队列；prepare只输出估算，不改判定。主性能目标是近MTU大包+少量小探针，纯小包只诊断PPS，不要求500M小包。参数真实接线缺口和计算方法见 docs/testing/NETWORK_CAPACITY_ENVELOPE.md；不得把计算当实测，或把MTU修复当Fixed30整体PASS。

执行状态：PENDING。提交后记录精确SOURCE/run与失败，核验后再更新范围；不得用本任务重启原工位已在途的请求。

首轮SOURCE 37bea82516b06f850663c4bc0a0e5aabda9f9b49：network-harness-check run39874672789 PASS；ARM run39874672683 编译/Go预算单测与Normal原生双向/Stop PASS。九组合边界中7 PASS；两个FAIL原样保留（artifact12467328308）。Fixed客户端outer1500/服务端1280在prepare失败：Rust client rx_wire_limit错误取server_limit，与按client_limit建立的LINK RX矛盾。Game2/1500小包正常、大于1200拒绝：GameAdapter与kernel入口仍硬编码1200/1216。它们是实际路径预算bug，不是VM容量或随机丢包。

下一SOURCE定向修复：Rust RX/TX限额取各自已认证方向，Game统一由每lane record预算扣31+16推导上限；保留既有2048slab和所有认证/路径门。加入Game超过旧1200的边界单测，重跑相同九组合而不重启压力矩阵。模型/文档后续提交f2c5811d未改产品，不影响首轮SOURCE归因。

第二轮产品SOURCE 1be5eb8e6832a59e7980cf8030435b9d71efd7ca，ARM run39875322487：构建/Go单测/Rust Game单测/Normal基础PASS；九种MTU正向与DF负向全部逐包通过，但整批8/9组合PASS。Game2的最终严格rejected=0门失败，两端各rejected=2，真实业务64/64、auth_rejected=0、Stop均通过。比原1200TUN变大后跨过IPv6最小接口MTU，推断Linux自动link-local/RS控制流量进入IPv4-only入口；不是业务大包边界再次失败。下一修复仅在新建owned IPv4 TUN启动前禁用其IPv6自动配置（不改host/global），保持原拒绝门复验；不得仅把rejected门调宽刷绿。原始artifact12468048305保留。

夹具兼容修正：只有显式WBD_ARM64_OUTER_MTU的用例传新flag，默认旧冻结包smoke保持原argv；增加bash语法检查。仅改变夹具时不需要重编旧二进制；本轮确实改了IPv4 TUN初始化，因此创建新精确SOURCE包。
