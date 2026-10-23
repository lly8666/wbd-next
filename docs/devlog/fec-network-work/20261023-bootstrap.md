# 独立FEC岗位启动

用户明确要求新分支/agent独立做FEC，并澄清先关闭外层数据重传，把FEC整套修好。分支从原网络实验45325c9c创建，隔离目录D:\codex\wbd\wbd-fec-network-tuning；未改原网络agent源码或status，未dispatch其任何任务。

本次准备任务入口、自己的status、永久接班提示词及工作流显式runner架构选择。无产品开关或FEC修复实现，无产品测试结果；运行时outer repair off尚待新agent接线/验证。保留原岗位的外层恢复算法修改范围，本岗位可做FEC及必要最小开关接线/配置/测试，真实receipt/RTT/keepalive继续工作。

上游产品99042008的原生构建/MTU记录只是恢复线索，不能代表FEC-only资格。新agent需核精确artifact和源码；原请求/在途Actions不重复。每个性能Action单一场景，唯一fec-work请求文件，架构显式arm64，按现有模板产物复用与同机A/B。
