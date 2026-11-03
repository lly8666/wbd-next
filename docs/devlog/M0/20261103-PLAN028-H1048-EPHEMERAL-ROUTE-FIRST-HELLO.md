# PLAN028 H1048 — 无人工 route-key 的首个 ClientHello 前材料

## 问题与方案

原WBD ClientHello识别使用 32B HMAC route-key；TLS exporter只可能在 ClientHello 后产生，**不是首次 route-key 解法**。用账户密码直接形成可公开核对的 HMAC 会向被动旁观者提供离线猜密码的验证材料；用公开常量或关闭识别则违背已明确的边界。

此包在**原 FakeTCP 三次握手完成后、首个WBD ClientHello之前**，按lane传两份固定37B冷交换：版本字节 `WB-R1` + X25519 临时公钥；服务器先写、客户端再写。两边用原Go标准库 `crypto/ecdh` 计算仅本次原始 association 持有的共享秘密，以 HKDF-SHA256 绑定两份临时公钥导出32B识别密钥，再调用**原** `ReadHello` / `markerFor` / uTLS。每lane新密钥，无公网固定常量、用户手工key、密码公开校验符或TLS后补算。只引入必要的冷前奏，**不改稳态 record、AEAD、PN、M4、FEC、重传和外层数据包格式**。显式 `--route-key-hex` 仍支持旧联机双方，空值才选自动模式；不同模式不允许默默回退。

临时DH公钥交换自身不是服务器身份认证。**自动模式强制 `VerifyServer=true`**，须由系统PKI/受信任CA验证真实SNI证书，才允许随后受保护用户名/密码写入。自签测试证书通过进程内 `SSL_CERT_FILE` 指向测试生成的CA进行信任，而非关闭证书验证；生产需要有效可验证证书。主动伪服务器不能绕过后续真实TLS证书验证获取明文密码。认出ClientHello不构成认证，实际账号/tunnel/IP仍受现有原 Go TLS后的 `Authenticate`、lease、generation和Rust承接控制。

## 完整接线与限定测试

同源码改写原Go V4双方 `EstablishClientV4`/`EstablishServerV4` 的会话前奏；Linux parse 默认空 route-key，Windows native V4 CLI允许省略，但老V3路径仍要求显式key。Windows共用主入口只一次性更新现有 assembly replace blob。更新原 assembly manifest 和自动测试：`net.Pipe` 四lane双方KDF一致、每lane唯一、损坏marker fail-closed；真实Linux原Game2两账号/Alice同安装A2唯一端口443/真正UDP、原TLS证书受信/Stop，沿用既有构建而不刷seed。原其他模式的显式key回归不改变。

**本SOURCE尚未原生验证：IMPLEMENTED_NOT_TESTED**。不冒称Android、Windows物理切网、所有七模式自动route已完成，也不覆盖H998在线MTU缩窄FAIL、ARM64 Game4FEC Action FAIL、远端ICMP未测或CPU因果未证。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1048 original TLS pre-ClientHello per-association X25519 route-key cold adaptation, default password-only clients with mandatory TLS certificate verification; Linux/Windows entry, server and genuine Game2 native fixture source candidate."}
```

## H1049 装配增量复核

H1048原Go分支构建Action缺新独立`v4_route_prelude.go`，报`undefined: v4AutoRoutePrelude`，Windows原Go assembly的main replace记录只改result_blob未补三个精确非覆盖patch，报`FEC2_ASSEMBLY_REJECTED: overlay result blob mismatch`。本增量按原workflow列表补齐冷helper和单测源、source/hash输入，Windows按此前确定的原源码patch精确合成唯一main，不重写恢复器、record或密码算法。修正前原生auto-route未运行，H1049仍是SOURCE候选。

## H1050 单owner原Go装配边界

H1049 原Go TLS/cold fixture编译已PASS。Win PLAN020严格拒绝重复owner时发现：新的唯一manifest已拥有`admission_v4.go`，但旧 Windows bundle 又试图复制同名文件。只允许已存在的原Go admission **与本SOURCE Git blob完全一致**时复用，任何不符、软链或其他新文件仍拒绝；不另造Go TLS owner。真实Game2账户密码自动route认证及Windows双OS仍需新Action。

## H1051 Windows相同源二次复制的唯一修正

`prepare_windows_wiring.py` 已通过完整manifest原Go装配后，自己的`EXTRA_BRIDGES`又将同一`admission_v4.go`当作全新文件写入，触发`competing original/overlay owner`。只对该文件在已经由唯一manifest安装且和同SHA原Go overlay逐字节相符时**不再复制**；其余Windows独立文件仍执行旧严格不存在检查。无多余恢复器、不修改原认证决策、未主张Windows真实路径PASS。
