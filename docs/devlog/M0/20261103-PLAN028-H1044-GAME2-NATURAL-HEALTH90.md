# PLAN028 H1044 — Game2 Rust 原生自然90秒死亡、另一账户持续业务

H1038 的 `NativeM4Alive` 冷读回只验证了接线，没有真实长达90秒失联后同443另一认证 Game2 组保持正常的生命周期资格。本包扩展已验证的双账号/单Rust TUN/原Go TLS四netns原生夹具：A客户端真实停止、B每约5秒持续经TUN发收UDP。服务端不得人为Stop或伪造计时，等待原Rust 15s Health/90s dead 状态；断言85–130s内恰一次服务端 `reason=authenticated-rust-game-health90 remaining_flows=2`，在旧A Stop后B继续收发，最后server Stop只退休B的剩余group。

**原生验证 PASS（限定）**：SOURCE `39df67722f2deab28b3d0600c5810df70bcb1743` 的 [Action 41650275157](https://github.com/lly8666/wbd-next/actions/runs/41650275157) `SUCCESS`，已下载并独立核对 artifact `13236259505` 的 `fixed-kernel-result/manifest.json`、本场景日志与同构建 Game4FEC6 日志。Game2 A 真断联后 **91 秒**出现原 Rust Health90 精确退休一次；B 在死区内/之后仍完成真实 UDP 回显。原 Go TLS、Rust SO 与客户端/服务端 SOURCE 和二进制 SHA256 见 [H1044 证据](../../../evidence/M0/PLAN028-H1044-SOURCE39DF-GAME2-NATURAL-HEALTH90-20261103.json)。旧 H1043 Windows 两OS Game2/4 多lane引导超时 FAIL 保留；不以 H1044 Linux 健康场景抵消。

此场景不证明全七模式、物理Windows网卡、Android或CPU/p99。H998物理在线收窄FAIL、ARM64 Game4FEC FAIL、远端ICMP未测与CPU因果未证照旧。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1044 authentic real Linux Game2 natural Rust M4 Health90 dead-group retirement while separate authenticated Bob group continues real native UDP; source-locked native Action success; Windows physical and seven-mode recovery still unqualified."}
```
