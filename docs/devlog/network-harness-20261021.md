# 2026-10-21 用户授权：可复用真实网络夹具

用户要求直接将周全的 Actions 网络工况夹具放入项目，复习先前测试规划。基于 main `87a3672` 创建隔离分支 `feat/network-scenario-harness-20261021`；M0 正在 Windows PLAN020 集成，未改其产品、cursor、registry或已接受证据，不冒充M0新任务。

复核 TEST_PLAN、FEC_V2_TEST_PLAN、真实 public V4 CLI、小回显和早期20Mbps夹具。现有公共入口已经支持Linux Normal/fixed/auto/Game，但 Game明确FEC off，TUN MTU1200固定，修复比例/算法等缺CLI；新夹具必须拒绝未支持参数，不能给假生效回执。

本次实现：真实公共二进制预编译artifact严格来源/hash复用；单Action单job单工况，AB/BA同VM顺序；独立双向UDP/TCP混合与RTT探针；大小包、阶段损伤、每向独立netem/GE/乱序/重复/限速、Game按lane黑洞；10ms首到桶、CPU/RSS/PSI/steal、实际网络队列与产品计数、Stop清理与缺测声明；18条可展开预置，不自动穷举。

验证计划：只在Actions跑夹具单测/真实socket自检及seeded netem能力检查；再以已接受构建源码 `bdcd66c6ccf973f26af7e9e4eb035457108cb7dd`、build39431226207、artifact12268980051跑一条双向10Mbps Normal/off、持续大小包60s、lossless开发基线。完整产品/Windows/物理/所有弱网矩阵不冒充已验。本提交是实现与测试intent，结果待独立收据补齐。

长期入口：`docs/testing/NETWORK_HARNESS.md`。不建立新治理、审批或交接系统；后续角色在既有devlog/evidence记录实际请求与run。

首轮Actions39618861340：7项夹具单测（含真实UDP/TCP双向）PASS，tc seed能力步骤FAIL；实际基线39618861434同样在开始发业务前FAIL，原公共两端READY与Stop均正常。根因Ubuntu24.04自带tc不认识seed选项。修正为请求显式区分seeded与unseeded_recorded，后者保存实际损伤/随机性限制且不宣称逐包重放；不安装浮动网络工具、不假造可复现seed。首轮原失败保留，产品持续性能仍NOT_RUN，修正后原样重试一次。
