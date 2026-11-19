# H2209｜复用旧P2非WBD普通TLS访问服务端的真实fallback

2026-11-19 M0从H2208继续。H2208 RouteKey v2源锁Windows Go向量/权限0600缓存3/3及build已[PASS_SCOPED](https://github.com/lly8666/wbd-next/actions/runs/44369630615)，H2206单网卡单IPv4旧SOURCE PASS_SCOPED；Android JNI与实体移动仍NOT_RUN。用户要求该小任务后复用老项目普通TLS访问处理。

源：原项目`lly8666/wobuzhidao`固定Go commit `a7a82db31fe736ffedee330795a3234d358f1984`，复用其`internal/realityfront/fallback.go`、`hello.go`、`candidate_deadline.go`、`fallback_test.go`已经验证的**只读一次ClientHello、按route-key认出WBD、其他SNI匹配才原字节回放到Decoy、双向splice及CloseWrite**，不复制第二套TLS proxy、observer或新wire。历史旧项目P2成功Action [35445121111](https://github.com/lly8666/wobuzhidao/actions/runs/35445121111)仅是旧SOURCE证据，**不作H2209产品PASS**。

本包在原`EstablishServerV4`冷路径给`V4ServerOptions`加opt-in`Fallback`；不识别原route-key的标准TLS走旧`FallbackFromHello`，新`ErrV4FallbackHandled`涵盖真实成功或被拒绝的普通会话，不挤占认证channel、不产生Go/Rust owner或lease；Server context Stop关闭同一association。原V4正常识别照旧cert/password和Rust session/Detach；无decoy不变。Linux `--decoy fixed-host:port` 只在server，冷路径验证、目标不能显式指向本机raw监听，5s dial/2min session/每方向64MiB；默认shared保护Normal/Game2/4，legacy专用Game监听不能安全逐lane分类，明拒decoy。单NIC/IPv4约束保留。

新增原Go source-locked真实FakeTCP/TLS夹具：标准非WBD真实uTLS wrong-key → 真TLS decoy → ping/pong/close_notify/唯一拨号/无Transition；相同WBD route-key正常认证→Rust handoff的原冷边界/decoy零拨号；错SNI→零拨号/非WBD不分配owner。Linux CLI解析正反例。测试执行前一律NOT_RUN，Windows/Linux原Go装配/单测按新冻结SOURCE记录，老029的独立Windows Rust DNS Direct单测FAIL保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H2209 reuse pinned original Go P2 FallbackFromHello in V4 server cold classifier for non-WBD same-SNI TLS; optional fixed decoy bounded splice, old protected WBD/Rust path unchanged."}
```
