# R0：Go 原生 TLS V4 opt-in admission （阶段子任务）

- why_now: cursor sequence6 要求把V4编码和epoch/KDF从test-only envelope推进原Go的受保护TLS请求/回复。此前只是旧Go V3向量 + 测试包装，不是两端真实TLS。
- 唯一代码源：`r0/go_overlay/internal/realityfront/admission_v4.go`（**非测试文件**），编译时作为新增文件加入旧SOURCE `lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984` 的 `internal/realityfront` Go package。旧仓库不写入，旧的V2/V3入口不被覆盖。
- V4使用旧`handshakeClientConn`/`handshakeServerRecognizedConn`、`ReadHello`、FakeTCP PrepareTransition/DetachTransition；一次TLS保护请求/回复，不增加握手RTT；读取前先限制长度，原旧Policy V3基准编码，版本4扩展24B；按规范认证后校验账号/Policy/租约与epoch，并对canonical reply做TLS exporter V4上下文与三套cipher的c2s/s2c HKDF。
- 此子任务的负面门：V3旧端拒V4（不静默降级），数据面未声明ready绝不发V4，零epoch只能创建无活动同身份隧道，wrong/join/duplicate lane拒绝，lane释放显式，store最大有界。不应凭TunnelID稳定复用而隐含新代。调用方必须真正具备Rust V4 feature才可标记DataPlaneReady；目前未具备，不能生产启用。
- 本轮原子done_when：编译Go1.23.12固定旧源码+新V4非测试源码，Actions真实TLS双方/拒绝/生命周期短例，产物编译一次、consumer精确hash后执行；记录成功或失败的SOURCE/run与一个下一动作，独立cursor-only H。
- 尚未满足R0完整退出条件：原应用调用点未接`EstablishClientV4/EstablishServerV4`，没有实际Rust数据面feature ready，未接多client真实产品/CLI/GUI；lane自动退出释放的全链路待后续生命周期施工；真实same TLS request重复/重发应复用response的服务端缓存尚未证明；C/平台ABI、Windows/ARM、产品性能/物理NOT_RUN。不得把模拟ready=true当已可对用户发V4。
- 下一动作：如Actions本轮通过，完成原控制程序的explicit capability/配置调用接线与fail-closed有效配置回执，随后Go↔C/平台ABI探针；如失败先定位首个具体反例，不通过换seed或掩盖。
