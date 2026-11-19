# H2206｜Linux服务端NAT友好网卡绑定、route-key输入安全边界

> **2026-11-19 H2208 新用户指令修订（覆盖本页下方旧密钥UX结论，不回写历史H2206测试）**：允许客户端与服务端输入相同8–32位ASCII英数字短Key，采用轻量v2 PBKDF2-SHA256 4096次、固定域隔离盐，本地一次派生32B；以后程序/进程重启读取0600持久缓存，短Key变化才更新。Windows本地用户配置缓存；Linux服务端/客户端可选密钥短文件及默认私有缓存；Android未来原生owner使用私有noBackup缓存，OpenWrt以0600短Key文件/私有缓存接入，**不因辅助组件存在宣称移动产品已联通**。原32B随机key配置保持兼容。短Key熵不足风险仍在，禁止宣称与原256bit等强。真实native/GUI/移动物理证据依各自SOURCE，不由本修订升级。


## 需求与选择

用户希望Linux ARM64服务端在NAT后无本机公网地址时仍可部署，并询问8/16/32位英数字串代替随机32字节route-key。

**已实现的NAT入口**：真实Linux发行程序 `wbd-v4-server` 的 `--raw-interface` 是必填底层网卡名（如eth0或ens5）；`--local-ip` 服务端可省略或设置为 `0.0.0.0`，程序在启动原有业务网络资源之前从**指定网卡**解析唯一的非回环、非链路本地IPv4并将该**具体地址**作为原Go AF_PACKET/BPF及原Rust数据面真实本地端点。已有明确 `--local-ip 192.168.50.20` 的行为不变。没有可用地址或有多个不同IPv4，拒绝自动猜测，要求显示选定；客户端不允许零地址。只做冷启动解析，网卡DHCP变化后需重启；不实现全接口无差别raw收包。

**部署示例（网关公网端口转发）**：

```bash
# Linux ARM64服务器实际收到 DNAT 后目标目的地址是内网 192.168.50.20
ip -4 addr show dev eth0
sudo ./wbd-v4-server --raw-interface eth0 --local-ip 0.0.0.0 \
  --local-port 443 --mode shared --tun-name wbdsv \
  --tun-ipv4 10.66.0.1/16 --lease-pool 10.66.1.0/24 \
  --server-name vpn.example.net \
  --route-key-hex-file /etc/wbd/route-key.hex \
  --users-file /etc/wbd/users.json \
  --tls-cert /etc/wbd/server.crt --tls-key /etc/wbd/server.key
```

路由器/云NAT必须将对外 **TCP/443** 映射到服务器的内网IPv4 **TCP/443**（公网客户端指向网关域名/IP），并放行必要防火墙；本地内网网卡自己不需公网地址。WBD使用Raw FakeTCP，不等于Linux常规TCP socket `bind(0.0.0.0)`；如Linux主机的TCP栈发送RST，须按既有部署手册在明确接口/端口上做有界防护，不能简单全局禁用RST。服务端证书和SNI需由客户端匹配；路由器公网端口和服务端--local-port不应假定能无条件重写额外业务层端口。若网关采用CGNAT且无入站转发，则单独部署中继、IPv6可达性或公网中转；仅本程序参数不能绕过CGNAT。

## 密钥安全结论（本轮不降低认证）

TLS建链契约要求route-key为由CSPRNG生成并离线共享的**32字节随机密钥**，供HMAC-SHA256路由识别；这不是用户密码、TLS证书或者业务AEAD主密钥，但会暴露公开的ClientHello随机数与标记，容易成为在线/离线猜测的目标，不能因业务另有TLS认证就视低熵无风险。

- **8位英数字串**：真正均匀随机的62字符字母表仅约47.6 bit 熵，**不安全，不能作为route-key本体**；人为自选通常更弱。
- **16位英数字串**：随机均匀最多约95.3 bit，达不到最低推荐的128 bit随机密钥目标；人工自选更弱，**不能直接替换本体**。
- **32位英数字串**：若严格使用安全随机源且每位均匀选62个字符，约190.5 bit（足够强的实用级别，但低于原始256 bit）；如果是用户可记忆的重复/单词/规律字串，则熵远低于190.5。经SHA256/HKDF扩展到32字节，只改变编码长度，**不能创造原本没有的熵**。本项目当前强制原格式，不自动引入弱兼容。
- **优雅无损方案**：保留原32字节密钥存储在权限0600的`route-key-hex-file`中；Windows GUI导入本地密钥文件，界面可显示一段8/16位的**别名/标签**，而不是拿它做认证。若要缩短需转录的密文，可用**43字符无填充Base64URL**无损表示全部256 bit（需双方配置解析新增接线和负测，当前版本尚未实现），不使用用户短密码替代。

现行可用命令：

```bash
# 在服务端创建后不要向终端或仓库输出真实key
sudo install -d -m 700 /etc/wbd
sudo /opt/wbd/wbd-v4-server --init-route-key-file /etc/wbd/route-key.hex
sudo chmod 600 /etc/wbd/route-key.hex
# 通过独立加密通道把相同原32字节随机密钥交付客户端（而非在聊天中贴出）
```

H2206修改仅限Linux服务端NAT冷路径/原生测试，不改变route-key密码学或TLS协议，符合 `docs/architecture/TLS_HANDSHAKE_CONTRACT.md`。想要自定义的8/16位输入，只能实现为**本机别名→原32字节随机密钥**的安全映射，不作为新密钥；其他安全取舍须明确变更安全契约后完整双端审核。

## 实测与限定

新源码 `039b88c4eda1edac24d4a9510373f4d127aea74d`，[原生Action 44353147584](https://github.com/lly8666/wbd-next/actions/runs/44353147584) 两独立Job SUCCESS：Linux x86_64和aarch64各跑 `local-ip=0.0.0.0` Normal/tls、`local-ip omitted` Game2/flows，实际原Go TLSv2、Rust、真实netns AF_PACKET/TUN、双向TCP/UDP、双边Stop PASS_SCOPED。原Action44351999455仅为外层CGO linker变量遗漏失败，已按源码修复重跑，不改生产热路径。没有测试实际公网NAT路由器或Windows实体机到ARM64实体机，仍为 NOT_RUN。

按M0计划PLAN029B，新增服务端NAT地址自动选择并不表示PLAN029整体完成或进行任何外部部署。
