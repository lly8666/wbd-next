# PLAN028 H1072｜同一 Go/Rust 二进制修真实TCP捕获，Windows所有原TLS夹具独立信任证书

H1071 原生 [Action41694943172](https://github.com/lly8666/wbd-next/actions/runs/41694943172) 已真实完成原 Go TLS/账号、应用专属CA及单端口443、Linux/x86_64 两netns原Rust收发5个内层UDP和双方Stop；其完整Action **FAIL**，仅因为最后的tcpdump经典PCAP由kernel `tcp port 443` BPF捕获后无法获得真实TCP载荷，离线 TLS auditor 报 `no actual TCP payload on 443`。此状态绝不记作标准TLS报文外观PASS。H1072 不碰原产品 Rust/Go 二进制，只把**隔离单接口** `wbdvs0` 的tcpdump捕获过滤扩为IPv4，仍由原 `m0_plan028_tls_wire_audit.py` 严格核特定443四元组/序号重组/首载荷ClientHello、服务端无提前payload、TLS1.3、SessionID32及扩展/record字节长度。失败时只有IP/端口/PCAP文件大小和tcpdump的简短信息写日志，完整PCAP在runner上删除，绝不上传。新增**一个**frozen native x86/x86 Action，下载 H1071 已真实构建的 [Action41694943009](https://github.com/lly8666/wbd-next/actions/runs/41694943009) `m0-plan024-linux-product` 工件 `13260387707`，逐文件 SHA256/ELF 源锁 source `d7bd355389c1233c54eaa6a4553ebadcbe0eeb70`；不第二次编产品，也不刷弱网旧矩阵。原 x86-wire build Action 在标记 `[frozen-fixture-only]` 的提交上显式跳过。

H1071 [Windows Action41694943037](https://github.com/lly8666/wbd-next/actions/runs/41694943037)：原Go证书+Rust Wintun Normal真实 UDP 双向/原Stop已经 PASS，随后 Fixed、Auto 原生测试的独立随机自签证书被当前**正确强制的x509身份校验**拒绝；这不是应该关闭证书验证的理由。把测试根证书局限在原 windowsownerlease 测试夹具，Normal/Fixed/Auto/Game 的服务端只生成一次真实私钥/证书，各独立客户端通过自有x509.CertPool验证，生产OS/GUI用户信任永不修改。对 Go donor-only `TestR0V4PrivateNativeBridge...` mock 只检查原 SYN 的合法不可伪造边界 `536<=MSS<=1460`，不依赖仅在另一个产品构建中存在的 `faketcp.PublicV4AdvertisedMSS()`；另有实际Rust冷路径和SYN包测试仍检查默认外层1460/MSS1420，用户默认不变。

静态R0历史审计源码卡了最新registry已经授权的revision4，但测试仍写旧revision3，H1072按真实 M0 main/global_writer/assignment_epoch 及 revision4 **精确比对**，没有放宽批准规则。Windows物理NIC切换、ARM64完整新TLS原生资格、H998热缩MTU、旧ARM64 Game4FEC旧FAIL与CPU/p99、远端ICMP范围均保持原状。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1072 freeze H1071 x86 Go/Rust native binaries for single TCP-stream first-flight capture after kernel BPF test failure; enforce trust in Normal/Fixed/Auto/Game Windows original Go test certs, dual-source MSS bounded test and exact registry revision4 audit; appearance not PASS yet."}
```
