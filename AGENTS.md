# WBD Next｜全体 agent 硬约束

1. **最新用户指令优先**。真实业务首到、低延迟/无跨流HOL、低CPU；允许有界内存。认证/完整性、账户/lane隔离、generation、原密文、MTU、安全重放、真实驱动和owned Stop不可退让，见 [PROJECT_CHARTER](PROJECT_CHARTER.md)。
2. M0在 `main` 单写者；全新会话默认上轮中断，先读 START_HERE、章程、registry、cursor 和相关 Actions，增量续接，不重复dispatch、不重扫旧网测、不复活旧FEC工位。
3. **PLAN027A于2026-11-03按用户明确指示限定范围收口**，不是“所有原技术出口 PASS”。[H998权威证据](docs/evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json)：11个Windows/WSL2原生范围内PASS；ARM64 Normal PASS、Game4FEC真实业务通过但 Action FAIL；在线物理 MTU 缩窄真实 FAIL；对端ICMP3/4未测，性能无旧新产品因果结论。原日志、source锁、历史失败不改写。
4. **PLAN028已由用户2026-11-03明确启动**，H1000只完成入场与依赖核查，不代表产品施工完成或任何028测试PASS。[028开工入口](docs/prompts/M0-PLAN028.md)，并复用 [MTU_CONTRACT](docs/architecture/MTU_CONTRACT.md) 的Rust统一预算。027A尚未解决的在线收窄请按028§4.1–4.2真实网络切换、重认证和新路径预算处理，不冒称原已解决。
5. Go保留成熟TLS/OS/GUI冷控制，**标准TLS建链/报文外观为红线**，禁止ClientHello前私有前导/交换或套伪TLS头；允许预共享route-key，唯一规范见 [TLS_HANDSHAKE_CONTRACT](docs/architecture/TLS_HANDSHAKE_CONTRACT.md)。Rust稳态，禁止Go逐包FFI/空轮询/双控制器。普通实现自主决策，不叠防御通用框架。
6. 完整同批改双方/配置/夹具/功能卡后冻结SOURCE；一Action一场景，不同场景可并行，同VM A/B顺序，一次构建按SOURCE/manifest/hash复用；不刷seed、不把不同OS/VM结果当因果CPU增益。
7. main不reset/force、不覆盖未知变更。短devlog、证据、功能卡、cursor及时更新；旧SOURCE PASS≠新SOURCE PASS，失败/未验/物理资格原样记录。用户普通入口外层完整IPv4 IP MTU固定默认 **1460B、不含L2**，1500B仅显式最大；内层Rust预算自动推导、OS读回，不回写外层用户设置。无凭据/大pcap入库，不擅自部署物理机或发其他会话消息。
