# M0 2026-10-18：R0-023 安全先行与下一阶段产品接线图

本页记录 2026-10-18 实际工位快照和本轮 M0 原本已经授权的 R0-023 安全演进。**这是协作/产品依赖顺序，不是新分配或 G3 产品范围变更**；控制权威仍是 main registry，动态进度以分支 cursor、SOURCE 和 Actions 为准。不要凭本页将 worker 标 idle、FEC2 ON 或产品通过。

## 实际工位快照（2026-10-18）

| 角色 | 本轮任务 | 精确交付 CODE / 事实 | 动态缺口 |
|---|---|---|---|
| M0 | R0-M0-V4-PROTECTED-OWNER-COMMIT-023 | 原实 Go↔Rust 1370/1728B LINK 双向两片 SOURCE 821962b7，run39089250014 PASS；新源 dd01c86b 封包前整包分片 M1 slab 预备待 Actions | 2048B 原TUN入口与单轮32条上限、Stop/MTU收缩、原驱动 prefix/unknown、同一真实产品持续业务硬门未收口 |
| M1 | R5-M1-FEC2-OWNER-SCHEDULING-014 | CODE 3f78a671，worker-native39082738345 130/130 PASS，H19 `blocked` | 最新中央 scope/H19 未确认为 PASS；M0 真组合与成本 NOT_RUN，无新独占代码障碍 |
| M2 | R2-M2-AUTHENTICATED-REPAIR-INGRESS-WORKPACK-010 | CODE 654a3c12，worker-native39045616456 70/70 PASS，H25 `ready_for_integration` | Go 原认证、M1 frozen arena、M4 prefix/uncertain live edge 未由 M0 接线 |
| M3 | R5-M3-FEC2-CODEC-NATIVE-017 | CODE8cc5b06d，worker标量122/0/1；M0 Linux x64 true ISA-L F2 11/11 PASS及同机400000编码+e4恢复/腿合格 CPU 窗 SOURCE f088ca04 run39090941413 | worker H/治理、完整ARM64/Windows新 V2 codec 源码原生校验仍需区分；模块微基准≠产品 |
| M4 | R5-M4-FEC2-COLD-POLICY-PLATFORMS-014 | CODE 7cef7e84，原Go冷策略8/8；Linux x64/ARM64/Windows safe-wrapper各2/2，H21 `ready_for_integration` | 产品真实 CLI/GUI/配置生效 ACK、Rust FEC2控制 admit、Windows loader/应用级全链路 NOT_RUN |

## 依赖优先级：剩余的是产品端到端门，不是5个独立工作包的百分比

1. **P0：R0 正常/off 原路径安全收口。** 唯一 Go 认证→Rust 原owner→M4 raw/TUN 主路径；跨轮次大合法 UDP、一个片发出后 MTU变小不能混 stride、前缀/不确定内核完成、Stop归还 loans、可运行持续业务、已知 DATA 丢失后小包不 HOL。保持FEC2 off。先充分收口后续共用的生命周期/路由不变量，避免FEC新功能叠加到脆弱的基础。
2. **P1：仅对已经交付的 worker 组件分阶段整合。** M1 三class、Game shared sender、M2 receipt/frozen/repair和 M3 codec 在原owner类型及原 M4 driver lease 上运行；从真实 Go V4 拿认证、generation/epoch/方向上下文。先完整 functional/资源界，不急于启配置开关。失败按归属回交负责工位的具体反例，不重复分配已完成包。
3. **P2：FEC2 一次受保护能力协商+真实路径。** 建实 source10/repair12/k1..16/r<=20 与原 AEAD/PN、LINK/FrameBudget、M1 首源/期限/parity、M2 authenticated receipt；FEC2 bit2/kind2/3 从预留变实际只能在 hard gate 后按双方独立能力启用，默认仍 OFF。证明确实接过 Rust FEC2，非仅跑 Go policy replay 或 x64 microbench。
4. **P3：Go 唯一配置/产品入口。** M4 七档/两方向auto、一客户端一个 applied revision，接原 CLI/GUI/参数目录、reload/fallback/rollback、旧设迁移与用户实际看到的模式一致；Game只 fixed/off，禁止auto静默打开。Linux/ARM64/Windows safe wrapper 构建不代表 V2 Windows loader/product PASS。
5. **P4：完整业务路径与恢复/Game 回归。** Normal fixed/off/auto、Game2/4 的真实多客户端/双向、稀疏首发/来源、parity公平与shadow重传10%独立账本、真实 Lost DATA、换代重连/未知syscall outcome/IPv6默认处理、DNS/LAN/分流迁移清单。旧版80s中断风险保留R6。
6. **P5：真实复用构建与基线/性能资格。** 按 TEST_PLAN 第0、2、3节：Linux Normal/off真实TUN/raw独立业务10Mbps/方向、热身10s测60s且 CPU/rss/actual injected/first delivered/drop完整；之后必要 RTT/loss、FEC2 N1/N2/N30/50/100、Game 3Mbps 与容量阶梯，不在不够容量主机盲冲500Mbps。对相同 workload 比成本必须同VM同SOURCE AB/BA，绝不能用 codec 57x 直接推产品吞吐。
7. **P6：可交付与物理验收。** 可运行的目标平台/安装、GUI服务启停、与原控制迁移行为逐项验收，实际 Linux ARM64/Windows codec-native和完整装载链、R6长时/80s风险、真实物理500Mbps另列，不因 Actions 部分绿色关闭资格。

以上7项是**剩余产品验收关口分类**，不是7个要新派工位的任务、更不是严格线性排程。可在基础/合同就绪后合理并行开展小的独立平台/恢复反例；总体阻塞链是 **R0 安全原路径 → M1/M2/M3/M4 实际组合 → 正式双方协议/配置生效 → 持续业务/弱网/三目标/发布资格**。可见的“工位空闲”主要是 M2/M4 模块已交接待 M0，并非“产品开发只剩最后5%”。
