# PLAN028 H1067｜撤除TLS前 WB-R1，原 Go 固定route-key+强制验证同包 SOURCE

**主线优先级**：用户 2026-11-04 明确撤销 H1048 pre-ClientHello 37B WB-R1/X25519，同时接受32B预共享route-key；先修标准握手红线，再续 PLAN028 lane/切网。基线 `bb2dfb8a1c39d82b89ec394a5691598ef01fa382`。

修改：原 `EstablishClientV4/EstablishServerV4` 在任何预外发/读取前要求32B route-key，不再调用 `v4AutoRoutePrelude`；删除旧源码与负面错误前导测试；原 donor tls.go 用同源码构造兼容HMAC 32B SessionID，只加 per-client app-specific `RootCAs` 支持，V4 强制 `VerifyServer=true`，不让显式key默认跳过身份认证。Linux原 CLI两个端点均强制key；服务器 `--init-route-key-file` crypto/rand创建0600且不可覆盖，双端 `--route-key-hex-file` 读取，客户端 `--tls-ca-pem` 特定信任。Windows原 native Normal/Game 都传 `RootCAs`；CLI config/原WinForms两个目录条目增加离线key与CA，显式路由key被严格限制32B。配置说明 `docs/decisions/M0-PLAN028-PRESHARED-TLS-ROUTEKEY-OPERATIONS-20261104.md`。

测试夹具：原 x86 Linux 真 netns/原Go/Rust/TUN单一场景通过离线key文件、专属CA、原 `v4_tls_handshake_contract_test.go` 的4 Game lane SessionID fresh/错误key/错误密码/错误证书/缺key无发包；真实tcpdump经典pcap只在临时runner解析，结果只保存client/server首record、TCP重组长度、扩展、hash与单位。旧Game AUTO_ROUTE开关不再允许重新协商，仅作为旧测试情景名并应输出新PRESHARED收据。旧完整 FEC/Health90 Matrix本提交不重派，以新 `m0-plan028-tls-wire-original-x86.yml` 精确SOURCE场景为主。

**资格尚未确认**：本提交仅 SOURCE_CANDIDATE；真正跑完 Go/原生 x86/Windows 源装配、Pcap结构等限定后再升格。Game4 H1064 x86物理切网旧SHA真实业务已观察，但原 Action FAIL 且TLS外观按新契约不合格；H1065冻结旧二进制脚本改为手动历史入口，不再同当前sha自动复跑。下一完整Linux平台工作包ARM64 client+server，不拿QEMU冒充。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1067 remove WB-R1 X25519 pre-ClientHello, require 32B provisioned route-key, mandatory cert validation for V4 explicit path, Linux Windows GUI original manifest aligned; targeted real TCP/TLS wire qualification pending."}
```
