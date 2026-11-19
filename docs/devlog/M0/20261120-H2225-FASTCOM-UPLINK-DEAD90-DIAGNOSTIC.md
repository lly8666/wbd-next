# PLAN029 H2225 — Fast.com 上行阶段 Windows Health timeout 限域诊断

用户上传的 H2224 Windows GUI 日志，不将私有域名/IP/凭据提交仓库：
- Generation 1 READY 01:29:56 → Rust HEALTH_TIMEOUT 01:32:30，约154秒；断时 TX 54,764 records，RX 29,497 IPv4 delivered，Npcap kernel local drops 0。
- Generation 2 READY 01:32:39 → Rust HEALTH_TIMEOUT 01:35:04，约145秒；断时 TX 63,558 records，RX 33,310 IPv4 delivered，Npcap kernel local drops 0。
- 两次均报告 dead_after_seconds=90，Stop/WAL恢复后原 Go TLS 重认证。不是上线后固定150秒断；原 Rust HealthClock 从最后收到 M3 AEAD/唯一PN认证业务或Health起计90秒。旧报错混合未收到认证入站90秒、已认证远端退休，不能从旧日志区分。
- 仅用户描述 fast.com 上行阶段断线，尚无同期 Linux ARM64 服务端 Health/TUN/AF_PACKET/Stop 证据。Npcap local drops=0 不证明线路或远端无丢包。GUI 2秒只读状态检查是观察到 Rust 已判死的地方，而不是导致判死的定时器。
- 此次日志为 fec-fixed profile=5，未展示 Auto 链接。Auto 的 S2C=unknown 为没有服务端认证态实际档位回读；所有模式 GUI RTT 和首发损失为 unknown 是产品 V2 数据生产者写死，不能凭空补数字。

## H2225 原生诊断，仅在真实 Rust Health dead Stop 时输出一次

- Rust HealthClock 新增只读 last_authenticated_age_ns/attached_age_ns/local_business_age_ns；不将本机TX、普通 TCP ACK、未经AEAD认证的数据当对端在线。
- 在现有 Native Owner Mutex 下仅最终 terminal verdict 输出 WBD_WINDOWS_RUST_NATIVE_HEALTH_TIMEOUT 的 cause=authenticated_peer_retire 或 no_authenticated_inbound_90s；同时显示 last_authenticated_rx_age_ms、attached_age_ms、local_business_age_ms、retire_notice_sent/attempts。
- 不改变原Go TLS、Rust AEAD/PN、15秒Health、dead90、FEC、业务时序、重连/Stop或内核WAL逻辑；无 Go 每包回调。
- 原生 Windows Action 44584194578：89 Rust native owner 测试 +15 Health 测试 PASS；新增单测覆盖上传本地业务不会刷新 authenticated RX 和真实 peer retire 区分。此 CI 并非公网实机复测。

## 后续实体复现

必须安装包含本改动的新版 Windows 客户端，采集新的 cause/last_authenticated_rx_age_ms；同期采集 Linux 服务端同一 TLS lease 的认证 Health RX/TX、M4/TUN/内核 drops、Stop原因。对比空闲4分钟、单独下载、限速上行和不限速上行；只有双端证据才能归责上行拥塞/对端Health发送饥饿/认证peer retire。H2220物理失败仍留存，PLAN029完整技术出口 OPEN。

```feature-impact
{"kind":"none","reason":"H2225 only adds terminal original Rust Windows Health timeout diagnostics and tests, with no protocol, FEC, GUI or runtime authorization behavior change.","ids":[]}
```
