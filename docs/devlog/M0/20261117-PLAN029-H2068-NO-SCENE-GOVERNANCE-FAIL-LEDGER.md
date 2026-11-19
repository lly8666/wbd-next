# H2068｜H2067 原生构建通过，治理边界与历史 FAIL 严格登记

本提交仅修复冷启动 Health 修复批次的治理/feature 证据链，不动任何 Go/Rust、Workflow、数据面或版本来源，也不触发原生新一轮场景。

前一批 H2067 产品 SOURCE `2fca1a93b4f9f7d3e7c5985adc356ade13332e86` 已通过 Windows Go+Rust、Linux Go+Rust 同源编译与两端单元，并在主 Action [44022456867](https://github.com/lly8666/wbd-next/actions/runs/44022456867) 上传新 Windows EXE/DLL 和 Linux peer。自动派出唯一两个独立原生 Action：[域名44023823956](https://github.com/lly8666/wbd-next/actions/runs/44023823956) 与 [TTL44023829996](https://github.com/lly8666/wbd-next/actions/runs/44023829996)。用户正常 GUI H2061 两代测试保留于主构建 Action。三场的第二代 **当前均未收到合格真实结果，不登记 PASS**。

上一个 H2066 SOURCE `4633f9e8c1da206401ee8952db07e2e65c83fb8d` 的三个 Action GUI44020809932/domain44020814338/TTL44020818591，确实经内核看到两个不同 TCP Source Port 的 SYNACK 且二次 TLS 认证通过，但服务端 `V4_PUBLIC_MULTI_SERVER_B_CLIENT_UNPROVEN`、第二代 authenticated M4 Health/路由/OS/business 失败。将这两张功能卡补录**显式 FAIL**，保留旧版本原始记录；此前 DSL 声明的另外两张卡已有更新。历史 NOT_RUN/极端压力仍不改 PASS。

本提交也将 M0 cursor 的三段冗长进度压缩，保留当期精准 Action IDs、Stop/实网下一个门槛，使其不再超过治理 `max_hot_bytes=32768`。这仅是治理容量修复，不宽免结构检查或不合格产品网络证据。

```feature-impact
{"kind":"updated","ids":["client-domain-bootstrap","gui-config-feedback"],"reason":"H2068 preserve true H2066 second M4 Health failure in cards and retain H2067 product physical verification as pending"}
```
