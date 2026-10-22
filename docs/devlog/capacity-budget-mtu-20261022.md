# 极限参数闭环与自动内层MTU

2026-10-23，用户直接授权；基于 main d8ba2cf2，独立分支 fix/capacity-budget-mtu-20261022。先核原测试工位的 S030/S031，不覆盖其 status/cursor，不重复压力请求。S030 每端约7k输入被 record1180→FEC source1135 拒绝；c297a805 的固定1280修复是根因依据，按用户最新要求改为外层配置自动推导内层TUN，不能停留在更换固定常量。

代码：Linux CLI --outer-mtu 默认1500；取接口MTU、MSS、双端已认证record limits的共同约束，扣record31/FEC14/Game16；建链后、Rust读取TUN前应用。Auto保留FEC空间，所有lane只收紧共有TUN。无需逐包计算/新wire字段；保留现有Rust path/DF硬门。Windows另一入口由M0并行维护，本次只给统一迁移语义，不宣称已接线。

测试：Actions构建原Go+Rust ARM包、Go预算反例；同包九个便宜功能组合（Normal/Fixed/Auto×1280/1500、双端不同配置、Game2/4），读取实际MTU后验边界与超限DF及Stop。这是功能批次，不是性能比较。独立 network-harness-check 跑模型及夹具合同；性能压力继续由原测试工位自己的单场景Actions推进。

模型与方案：tools/network_harness/envelope.py 复用 cost_model，区分外层/内层、包数权重、partial FEC、Game复制、保留缓存与短发送队列；prepare只输出估算，不改判定。主性能目标是近MTU大包+少量小探针，纯小包只诊断PPS，不要求500M小包。参数真实接线缺口和计算方法见 docs/testing/NETWORK_CAPACITY_ENVELOPE.md；不得把计算当实测，或把MTU修复当Fixed30整体PASS。

执行状态：PENDING。提交后记录精确SOURCE/run与失败，核验后再更新范围；不得用本任务重启原工位已在途的请求。
