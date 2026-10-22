# 2026-10-22 用户授权：完整网络矩阵与宽松合理的恢复目标

基于远端main `5a6bf52521047184107e4c67a9a04016cf4a410f` 创建隔离分支 `docs/network-matrix-20261022`。用户要求同类工况并行、容量不足跳过、500M/2%/单程200ms、50M/30%/单程300ms、off修复预算/内层业务、四lane、自动档、换代/idle/keepalive/黑洞与遗漏项。未改产品、registry、任何worker cursor；没有dispatch或跑本地产品测试。

读取当前FEC2设计、已有模型、修复预算源码、主线M0进度及PR21夹具。发现已有maximum16:20满组IID30%模型残余0.02282576%，不需先新增全局更高档；partial和相关损伤必须单列。预算实现R/F≤10%，稀疏32KiB/s floor另有进程约束；高损off的理想低残余不符合预算，不能用零loss验收。

新增 `docs/testing/NETWORK_MATRIX_20261022.md`：37条有条件场景，先8个代表点，6个独立Action并发上限，高负载最多2个；同job新旧顺序比较、host/生成器与产品瓶颈分层、真实字节/PPS/BDP、独立/共同Game损伤、统计与deadline、原始失败保留及有限停止。解析模型数值另存 `docs/testing/network-matrix-20261022-model.json`，明确MODEL_ONLY；不是单元/产品/性能PASS。

按用户允许过渡损失/降档稍慢的本轮授权，将方案中普通auto选档参考从0.1%调为0.5%，降档20s/级，保留有效覆盖/完整性/无HOL等硬门；最高档持续IID30%的业务≤1%目标单独定义。同步更新FEC设计/专项测试与总TEST_PLAN入口，避免新agent继续拿旧过严时间门刷测试。控制器是否已经采用新参数须由M0实现和验证，文档不冒充代码生效。

科学依据：系统型MDS q=p*Pr[Bin(k+r−1,p)≥r]，两次修复q=p³及开销p+p²，四lane独立联合q(p⁴)，相关丢失不能套独立；线路容量包括FEC/lane/repair。参考RFC5510与tc-netem官方手册，未复制长文。CPU和工程p99没有虚构通用理论上限。只做计划/解析计算，Actions执行与生产参数修改均未进行。

## 后续授权：监测、诊断与轻量接班

用户要求高效率发现堵点、强制在修复前复习历史设计，并决定是否新增工位。只读main到a22c4e09baf7c42a39b4eab1d7c3febffc5a6836及registry/GOVERNANCE，确认M0仍推进真实Windows接线，现有M4已reserved，M1/M2/M3范围有明确限制。决定不新增工位，网络测试优化继续M0、允许全新聊天接任；Actions并发提供测试并行，独立模块才一次派完整包。

在同一PR #22补矩阵第9节及 `docs/testing/NETWORK_TRIAGE.md`：最低监测字段、1Hz有界快照/抽样成本、逻辑单位与in-flight/ready队列区分、可解释的故障特征、先定位再复习再修复、定向反例/默认性能复验、已有cursor热摘要和恢复/归档。M0长期提示词/GOVERNANCE只增加稳定入口；未改live registry/cursor、没有停止/发消息给其他聊天、没有启动性能测试或宣称监控已实现。
