# 网络测试方法与当前任务

M0 在 main 开发；具体整改/验收任务只读 main registry.goal 与 M0 cursor。当前 [主线完工包](../decisions/M0-MAIN-CLOSEOUT-20261028.md) 已吸收最新失败和容量模型，旧实验分支 status 不再决定 M0 的下一步。独立 FEC 工位历史任务完工。

## 保留的设计与夹具
- [机会式外层重传与MTU v3](../decisions/NETWORK-OPPORTUNISTIC-REPAIR-MTU-20261023.md)：一次、低CPU、fresh不受cache门控、预算分母与统一MTU。
- [容量模型](NETWORK_CAPACITY_ENVELOPE.md)、[矩阵](NETWORK_MATRIX_20261022.md)、[夹具](NETWORK_HARNESS.md)、[诊断](NETWORK_TRIAGE.md)：按当前场景选取，不从旧全量矩阵第一行重新跑。
- 旧FEC实验/网络测试说明用于查历史授权和失败；只在另有明确独立worker授权时按其分支工作。M0源码、修复和可复用夹具回main。

每性能Action一个场景/一个测量job；旧新同VM顺序AB，独立场景可并行。编译一次固定SOURCE/manifest复用。先校验注入、包长、限速在损伤前还是后，再解释残余/CPU/p99；host容量不足停止更重同族。修复后只重验反例和影响面，历史结果不抹掉、不自动移植到新版本。
