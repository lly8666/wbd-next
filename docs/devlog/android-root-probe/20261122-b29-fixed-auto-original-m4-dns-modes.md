# B29｜Fixed/Auto 原 M4 DNS 跨模式冷授权接线

基线 `09f1a12de71f2a99831593ead23cc5d9961cc9ff`：B28b [Action #44959984802](https://github.com/lly8666/wbd-next/actions/runs/44959984802) 11 SUCCESS/4 SKIPPED仅Host/BUILD。按用户最新指令暂停等待实机，优先修已接功能间的生产接线，不加防御性安全代码。

## 原始断点

B17/B19 已将Root App Fixed/Auto接到原Go TLS feature7及原Rust FEC2 M4；Root App默认 `tunnelDNS.setChecked(true)`。原 `V4LinuxClientProduct.ConnectAuthenticatedPeer` 在配置FEC2 PENDING及M4启动前按配置调用Tunnel/Physical/CN DNS冷授权，但Android Go bridge三处及Rust native三处均要求feature3，故选Fixed/Auto及默认DNS组合时必在M4前失败，尽管此前双ABI/Host构建成功。

## 产品直接修复

- Android Go三种原生 DNS bridge 接受真实协商feature3 Normal/off或feature7 Fixed/Auto；不改变TLS、鉴权或DNS模式优先级。
- Rust三个冷授权共用原生产 `original_m4_dns_feature_allowed`：Normal feature3，或者TLS handoff已准备原FEC2 RX的feature7。Go随后原样配置FEC2 PENDING，然后真实M4启动。其已有Fixed source M3 AEAD/PN及逆向FEC2解包本就使用同一TUN原DNS query/response mapping与Stop；没有新增发送器/线程/逐包Java/Go。
- Rust生产DNS路由Host测试覆盖feature3/7与feature7无FEC2 RX拒绝；同源CI运行B6 DNS、B16分片、B18/B19质量、双ABI、签名APK、原Linux Oracle，App静态门核对Go/Rust三处实际接线。新 SOURCE CI未完成前不报BUILD_PASS；Android Fixed/Auto+DNS真机E2E、系统netd、业务CPU吞吐仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B29修复Fixed/Auto在默认Tunnel DNS及显式Physical/CN DNS时被Go/Rust feature3冷授权拒绝，共享原FEC2/M3/M4与Stop，不增加防御框架"}
```
