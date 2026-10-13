# PLAN-001：长期运行数据面架构与验证计划

日期：2026-10-14。任务范围为方案/治理/数学验证，没有Rust产品实现，没有部署或修改旧项目源码。

## 已核事实

- 接手 main `cf8745ef4baf28c494a4fe6ebec1affd1aff79fe`；先前GOV-001已通过，角色M0 epoch/revision1，M1–M4仍reserved。没有未完手动request需要重复dispatch。
- 按原始逐条聊天与旧项目固定SOURCE `a7a82db31fe736ffedee330795a3234d358f1984`核对。旧FEC已有SIMD，MTU公式已改，N4控制层和N2部分资格仍未收尾。
- 新用户指令要求新旧同Actions顺序对比，明确覆盖原禁令；实现request/receipt对两leg同job、来源、hash、时间顺序的验证，防止只改文档却仍被工具挡住。

## 交付

`docs/architecture/`包含架构、恢复、成本、迁移、测试和来源。Go冷层+Rust同进程热路径；Game共享FEC/独立AEAD；ISA-L GF256保留原矩阵；aws-lc-rs独立AEAD；最多两次有界恢复，稀疏例外。500Mbps按PPS/RTT/字节算，给出源包FEC残损模型和合理判定。

治理入口/固定提示词同步更新，产品实现仍NOT_STARTED。模型是Python标准库离线公式工具，只在Actions执行；独立枚举小FEC/重试情形交叉校核公式。性能实施夹具尚未创建，不能把paired契约测试当成旧新产品A/B已完成。

## 验证/下一步

此提交随push执行Governance及cost-model，结果在后续证据补记。若中断，先查该精确SHA的原run，不重复派发。核receipt/manifest/最终conclusion后完成S/H。下一项R0最小接口/精确依赖与基线/编译复用，正式分配后再写产品代码。

没有用架构方案关闭N2 GE尾延迟、旧80s中断、旧MTU压力或Windows native问题。所有旧机器凭据/原始聊天摘录仅本机忽略目录，未进入公开提交。
