# PLAN-007 · FEC v2 公共接口冻结与工位单一写入者

已正常合入规划PR#10 main `365cbbcffdac5773a0a151a8c6b0dc5be5fb4f52`。本页是**实施接口约定，不是产品代码/资格**；原始标准 `docs/architecture/FEC_V2_BALANCED.md` 和 `docs/architecture/FEC_V2_TEST_PLAN.md` 不被覆盖。worker 必须先读主线 registry 对应 assigned_task，保留以前工作包的 SOURCE/历史 FAIL。

## 模式与记录
- 冻结新 scheme 标识 `fec_v2_rs16`。主线实际 `r0/go_overlay/internal/realityfront/admission_v4.go` 目前仅接受特征 0x0003（bit0 Receipt+bit1 Game）；**预留 bit2=0x0004**，由 M0 在原TLS V4受保护协商/KDF与真实 Go→Rust 通路完整验证后才启用。禁止直接改旧扩展的严格相等或默认生产开关。未声明支持者不得降级假装成功。
- 现有认证后 kind 0=LINK、1=HEALTH；**预留 kind2=FEC2_SOURCE，kind3=FEC2_REPAIR**。原record AEAD/8B HP/PN不变。只在协商过的新上下文识别2/3；旧LINK/WBDLFRG1分片不是新FEC2包，不能用魔数嗅探。M3在其codec内实现新类型；M0是公共导出、ABI及认证/kind adapter的唯一接线者。
- 按新设计单独采用GF256 0x11d、k=1..16、r=ceil(k*rho)≤20、Cauchy `x_i=i, y_j=32+j` 首行 XOR/k1重复；SOURCE=BE block_id:u64 + source_index:u8 + flags=0:u8 + 原LINK frame（10B额外）；REPAIR=BE block_id:u64+parity_row:u8+actual_k:u8+symbol_len:u16+GF body（12B额外），数学符号 `original_len:u16 || frame || zero_tail`。公共预算FEC2只预留14B，Game16B/LINK20B/record实际开销各扣一次；Normal/FEC off保持原快捷路径及已测 `fca4456313e59c0a67f4d8b98959a62d2af71b12`。
- 跨模块语义（先冻字段/方向，不强制worker修改其权限外的 `wbd-types`）：M3提供borrowed-input、owned-output、`encode_into`、解析/校验和typed status；M1提供`SourceReady, ParityJob, AppliedPolicyRevision, ActualK/ActualRSent, DeadlineExpired`及复用Arena/Stop/loan；M4提供唯一Go冷函数输入 `VALID/UNKNOWN/CENSORED/HOST_CAPACITY` 的每client/方向质量快照及 `SetTxFec(profile, revision)`意图；正式跨crate/C ABI、真实配置/UI与Actions入口只由M0统一冻结/实现。不得各建第二条生产热路径。

## 并行且不冲突
- M1现行R5-FEC2 owner包独占既有 `crates/wbd-engine/src/runtime/`、`memory/`。按class源包率lambda，EWMA有业务时250ms更新；`T=clamp(1.5×15/lambda,Tmin,C)`，Normal Tmin4ms/C clamp(SRTT/4,8..24ms)，Game Tmin2ms/C clamp(SRTT/8,4..12ms)，无RTT启动6/3ms，孤立`lambda*C<1`提前闭合；满16立即关闭；原包即时ready不等group，不让Game慢lane阻隔其他lane。parity期限/内存/Stop有界，不改M2修复预算/真实Go V4 owner。
- M3现行R5-FEC2 codec包独占 `crates/wbd-codec/`。保留已冻V1-016源码参考与旧测试，但V2不再要求旧Go数据格式逐字节相等。ISA-L实际后端/native对应 target要验证，不把旧组件CPU倍数当成新协议收益。
- M4现行R5-FEC2 policy/platform包仅新增确切原Go overlay两文件 `r0/go_overlay/internal/realityfront/fec_v2_policy.go` 和 `fec_v2_policy_test.go`，可在**原实际Go package**中实现冷策略纯函数；另一独占路径为 `native/isal-safe/build.rs` 的target构建。当前项目没有 `r1/go-bridge/` 实现文件，因此不能仅在无用演示文件声称产品控制已接通。M0负责真正使用的Go clone/overlay测试入口与其余 `admission_v4.go`/原生CLI/GUI/参数目录/共享Cargo和workflows。需要越权改现有Go文件，先交精确路径请求，不能私改。
- M2现行恢复010已经SOURCE 654a3c1验收待命；只有实际数据面反馈质量统计缺口确证后才由M0另派最小工作包，不重新开发RACK/预算/新修复队列。
- 未把任何new capability和kind在产品激活。M0仍沿原R0-023原业务安全集成/MTU/Stop推进，精确旧 D10 run39032995995 FAIL 保留。主线旧组件+新模块导入 `ede83b98edba1fee6f73bc99454040cc95392d4d` 的codec合批240秒超时 run39047975666/39048697568仍FAIL；P10 A→B +4.58%与B→A -1.46%矛盾，SPARSE B p99 168→196us/341→394us偏高，均不得标FEC2基线/产品PASS。所有源码证据、NOT_RUN和回退均按原S→H规则。

每个worker完成工作包内实现、针对性Actions正确性/适用成本、SOURCE/产物和devlog/evidence后才ready，普通提交无需等M0。一个性能Action只跑一个场景、同job/VM顺序A/B或B/A；真实Go身份、完整MTU/Stop/lease/恢复/能力和产品资格由M0集中验，不跨runner绝对CPU相减。
