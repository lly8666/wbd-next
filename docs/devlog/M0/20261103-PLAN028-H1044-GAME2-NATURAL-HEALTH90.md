# PLAN028 H1044 — Game2 Rust 原生自然90秒死亡、另一账户持续业务

H1038 的 `NativeM4Alive` 冷读回只验证了接线，没有真实长达90秒失联后同443另一认证 Game2 组保持正常的生命周期资格。本包扩展已验证的双账号/单Rust TUN/原Go TLS四netns原生夹具：A客户端真实停止、B每约5秒持续经TUN发收UDP。服务端不得人为Stop或伪造计时，等待原Rust 15s Health/90s dead 状态；断言85–130s内恰一次服务端 `reason=authenticated-rust-game-health90 remaining_flows=2`，在旧A Stop后B继续收发，最后server Stop只退休B的剩余group。

源锁Action验证前仅 IMPLEMENTED_NOT_TESTED；此场景不证明全七模式、物理Windows网卡、Android或CPU/p99。H998物理在线收窄FAIL、ARM64 Game4FEC FAIL、远端ICMP未测与CPU因果未证照旧。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1044 authentic real Linux Game2 natural Rust M4 Health90 dead-group retirement while separate authenticated Bob group continues real native UDP; source gate pending."}
```
