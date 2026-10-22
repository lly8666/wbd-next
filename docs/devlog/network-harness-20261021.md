# 2026-10-21 用户授权：可复用真实网络夹具

用户要求直接将周全的 Actions 网络工况夹具放入项目，复习先前测试规划。基于 main `87a3672` 创建隔离分支 `feat/network-scenario-harness-20261021`；M0 正在 Windows PLAN020 集成，未改其产品、cursor、registry或已接受证据，不冒充M0新任务。

复核 TEST_PLAN、FEC_V2_TEST_PLAN、真实 public V4 CLI、小回显和早期20Mbps夹具。现有公共入口已经支持Linux Normal/fixed/auto/Game，但 Game明确FEC off，TUN MTU1200固定，修复比例/算法等缺CLI；新夹具必须拒绝未支持参数，不能给假生效回执。

本次实现：真实公共二进制预编译artifact严格来源/hash复用；单Action单job单工况，AB/BA同VM顺序；独立双向UDP/TCP混合与RTT探针；大小包、阶段损伤、每向独立netem/GE/乱序/重复/限速、Game按lane黑洞；10ms首到桶、CPU/RSS/PSI/steal、实际网络队列与产品计数、Stop清理与缺测声明；18条可展开预置，不自动穷举。

验证计划：只在Actions跑夹具单测/真实socket自检及seeded netem能力检查；再以已接受构建源码 `bdcd66c6ccf973f26af7e9e4eb035457108cb7dd`、build39431226207、artifact12268980051跑一条双向10Mbps Normal/off、持续大小包60s、lossless开发基线。完整产品/Windows/物理/所有弱网矩阵不冒充已验。本提交是实现与测试intent，结果待独立收据补齐。

长期入口：`docs/testing/NETWORK_HARNESS.md`。不建立新治理、审批或交接系统；后续角色在既有devlog/evidence记录实际请求与run。

首轮Actions39618861340：7项夹具单测（含真实UDP/TCP双向）PASS，tc seed能力步骤FAIL；实际基线39618861434同样在开始发业务前FAIL，原公共两端READY与Stop均正常。根因Ubuntu24.04自带tc不认识seed选项。修正为请求显式区分seeded与unseeded_recorded，后者保存实际损伤/随机性限制且不宣称逐包重放；不安装浮动网络工具、不假造可复现seed。首轮原失败保留，产品持续性能仍NOT_RUN，修正后原样重试一次。

Actions39619133739（夹具7994b1a，产品bdcd66c）真实60s基线：C2S/S2C均103762/103762包、9.9999899Mbps、应用单程p99 0.4ms，probe597/597各向、Stop/owned namespace清理正常；产品CPU测量段12.07/12.03 CPU-s。原结果INCONCLUSIVE/Action failure，原因判定器以单个PSI峰值36.14直接否定样本；测量段平均PSI6.874，注入/交付均完整。原文件不改为PASS：修正通用判定器将真实业务结果与性能公平比较拆开，保留瞬时警告，持续争用使比较资格不确定而非直接认定host容量；添加反例测试。同步补实际时段首到字节、netem leaf/内核drop分账，TCP繁忙连接不阻塞其他空闲连接，rate_scale0不空转。重新跑同一基线用于验证判定器/字节计数变化，未改产品或损失门槛。

Actions39619547664（6abb59e）：8项夹具测试以及真实内核GE/限速/乱序/重复/四lane分类器全部PASS。只是夹具能力，不扩张为产品弱网资格。

## 2026-10-22 最终验收与交接

夹具代码 SOURCE `38c7e2fa8413c4de28690ef13bdd31ca04d2692e`；产品仍为 `bdcd66c6ccf973f26af7e9e4eb035457108cb7dd`，未改产品。独立 PR [#21](https://github.com/lly8666/wbd-next/pull/21) 交 M0 审阅集成，不覆盖其正在开发的主线。

- [39620189203](https://github.com/lly8666/wbd-next/actions/runs/39620189203) 与 PR 自检39620272660 SUCCESS：8项测试、真实双向socket自检和真实内核选项/四lane分类验证通过。
- [39620189243](https://github.com/lly8666/wbd-next/actions/runs/39620189243) SUCCESS / PASS_SCOPED_OBSERVATION：Normal/off，无人为延迟和丢包，60s双向持续大小UDP包；每方向103762/103762包，实际交付9.9999899Mbps，缺失/损坏/重复均0，单程p99各0.3ms，产品CPU测量段6.72/6.68 CPU-s，内核drop为0，Stop与owned namespace清理通过。该单程数是同宿主隔离网络结果，不是物理线路RTT。不能将此CPU与另一台VM先前12秒的结果相除宣布优化：产品完全未变。
- [39620260921](https://github.com/lly8666/wbd-next/actions/runs/39620260921) Action failure / INCONCLUSIVE，原样保留：每方向目标10Mbps（UDP5+TCP5）、1%外层损伤、50ms RTT、60s。实际netem两向约0.983%/0.996%；UDP注入各5Mbps，交付约4.977Mbps，缺失186/194包（0.359%/0.374%），单程p99 91.0/90.9ms。TCP受到真实反压，仅注入/交付3.665/3.645Mbps；已发送记录全部最终到达，但单程p99 792.6/1215.0ms，不能作为满目标速率PASS。无完整性或Stop失败，无UDP接收缓冲错误，无宿主争用警告。

混合场景产品M2全程修复计数1529/1496（合计3025），说明外层修复确实走到；内层TCP RetransSegs为908/924。全程计数含预热/控制，不能据此推断修复字节比例、有效修复率或多余重传率。TCP尾延迟包含内层TCP自身有序恢复和队列，不能直接认定整个隧道跨业务HOL；UDP仍持续到达。下一步应围绕这个已暴露的真实反压做一项有区分力的定位，不反复换seed或改宽门槛。

两条原始result已作为结构化证据保存于 `docs/evidence/network-harness-20261021/`，保留run、attempt、产品/夹具SOURCE、artifact ZIP与result entry SHA-256。baseline artifact12353544910 ZIP SHA-256 `d60a1686ac17ee015fee7ec7787d3baea7277b3bba9f4039fd925ad76be8ce0b`；mixed artifact12354920838 ZIP SHA-256 `2e9079fa4f030b6ac1b792bc71201dda3688850db2d90d490e8c4f6751568a5f`。未持久化大pcap、正文、凭据或产品二进制。

交付范围：可复用夹具及18个预置已实现，两个代表产品场景已执行；其余矩阵、Windows/ARM实机、Game+FEC和未公开的重传/加密调参仍未验证或明确UNSUPPORTED。详细内部FEC/修复时序继续NOT_OBSERVED。M0合并后可直接复用指南，不需重写夹具或重新编译同一产品源码。最终证据提交仅文档，不重新跑无变化的产品性能实验。
