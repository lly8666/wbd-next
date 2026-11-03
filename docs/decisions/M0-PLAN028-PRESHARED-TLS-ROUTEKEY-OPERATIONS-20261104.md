# PLAN028｜原 Go V4 标准 TLS、route-key 离线配置与证书信任

此文对应 `TLS_HANDSHAKE_CONTRACT.md`。**没有线上 route-key 协商协议。**完整 FakeTCP/TCP 建立后客户端第一条应用数据必须是真实 uTLS TLS1.3 ClientHello；既有 HMAC-SHA256(SessionID, random, normalized SNI) 在原兼容 SessionID 32B 域工作，不追加扩展或明文字段。server 收到普通/错-key ClientHello 的后续动作仍沿现有源监听器的识别/回落；绝无 WB-R1。

## 原 Linux 服务端先离线创建再导入

首次初始化（仅服务器本地操作，文件需处于隔离/受权限保护的配置目录）：

```sh
wbd-v4-server --init-route-key-file /var/lib/wbd-next/route-key.hex
# 只会创建不存在的 0600 正规文件，写入 crypto/rand 32B hex，不会覆盖旧配置；不打印密钥
```

原 Linux 服务端启动添加 `--route-key-hex-file /var/lib/wbd-next/route-key.hex`，正常还需原 `--tls-cert`/`--tls-key`、监听/用户等参数。客户端由可信离线渠道导入对应的32B route-key，提供 `--route-key-hex-file <本机权限0600的文件>` 或显式 `--route-key-hex <64个十六进制字符>`，两者互斥；没有key本地拒绝，不连接、不生成回退key。生产环境勿将key写到 shell 历史、日志或共享代码中。服务器 key 仅是入口分类材料，账户验证、设备安装 ID、租约仍由原 TLS 内 Admission 校验。

客户端配置 `--tls-ca-pem <本服务器PEM文件>` 可局部导入私有/自签服务器证书或其可信CA；不提供时仅使用原生 OS 证书信任根。无论 route-key 是明文配置/文件导入，V4 均强制证书链及 SNI 身份验证，未验证不得发送密码，不会安装系统级全局CA。正式自签部署必须把**正确服务器**公钥证书/CA通过独立可信渠道送到客户端，不能关闭验证。

## Windows 原 Go V4 CLI 和 WinForms 配置

`wbd-client.exe --native-v4-product` 继续沿原 Windows/WAL/Rust 真实入口，`--route-key-hex` 改为强制32B；增加 `--route-key-hex-file` 和 `--tls-ca-pem` 的原产品 flag 与 JSON config 字段，证书验证在Normal、Auto、Fixed、Game2/4客户端统一强制。现有 WinForms Portable 参数/标签清单同步新增这两个可导入路径字段，并继续把 `route-key-hex` 按密码字段脱敏；文件路径须引用受Windows ACL保护的便携数据目录，勿将密钥直接附进诊断。GUI本身不是 TLS 服务端；Windows 实际原生 NIC 路径切换仍需另行物理验收。

Windows 和 Linux 的用户模式不会凭 route-key 宣称伪装成借用站点或绕过检测：ServerHello、Certificate 和 Finished 均由成熟真实TLS库生成及验证，实际证书只能代表所配置服务器，而非借用站点私钥。

## 同 SOURCE 的有限验收及状态

H1067 将原Go donor、overlay manifest、Linux/Windows/GUI装配一起源锁。定向原生 x86/x86 场景实际采集 veth 443 从 SYN 后的两个方向、按TCP seq重组，再检查客户端首ClientHello、服务端无提前数据、TLS record/长度/SessionID与uTLS baseline结构；只把 hash/长度/类型脱敏摘要上送。客户端普通、缺/错key、错证书、错密码在同源Go测试验证；Game多lane复用同一SessionID构造流程，后续ARM/ARM与Windows实际网卡通路按任务轮换验，不能提前冒称。

变更仅Go冷入口和CLI/测试/用户资料，不调整Rust稳态/原Game/FEC算法。H1048–H1052旧 ephemeral prelude功能PASS仍为历史同SOURCE功能证据，TLS外观不合格。H998在线MTU缩窄FAIL、旧 ARM64 Game4FEC Action FAIL、Windows物理网卡/CPU/p99未验保留。
