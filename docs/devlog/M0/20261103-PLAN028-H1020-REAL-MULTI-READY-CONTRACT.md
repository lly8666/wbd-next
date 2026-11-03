# H1020｜PLAN028 H1019原生FAIL后修真实就绪状态契约，不降低业务门槛

H1019 SOURCE `d3d0be09571f21fe8da5789cad5af8c3143dbc55` 的 `PLAN012-COMBINED-REAL-GO` Action `41585432181` **FAIL**，源锁/native job `125749687963`。失败发生于原单设备回归测试 `WBD_V4_PUBLIC_AUTO_IP=1` 的就绪门，`M0_V4_PUBLIC_REAL_CLIENT_SERVER_NOT_READY`：日志证明客户端已实际原Go TLS成功、服务端给予实际随机`10.66.0.254/32`、Rust原始M4工作已启动；服务端亦已打印新的真实`V4_PUBLIC_MULTI_SESSION_READY role=server one_port=443 active_detached_flows=1 auto_lease=1 original_TLS=1 Rust_M4=1`。但旧测试仍要求只有手动IP老服务端才发出的`V4_ORIGINAL_GO_SERVER_NATIVE_READY`，故在真正UDP应用或后续三netns并发前误判NOT_READY。此项 FAIL 必须保留；**H1019绝非多设备PASS**。

H1020只修`tools/m0-v4-public-real-linux-netns.sh`两处原生产品就绪检查，以及同一套真实Stop的服务端凭据：自动IP新单端口原GoTLS manager必须报告`one_port=443`、`active_detached_flows=1`、`original_TLS=1`、`Rust_M4=1`才算就绪；其Stop必须同时证实**逐会话Rust owner** `V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=server-close`和独立**共享Rust TUN reader** `V4_PUBLIC_SHARED_TUN_STOP_DRAINED`。原手动IP场景继续严格要求`V4_ORIGINAL_GO_SERVER_NATIVE_READY`及原Rust Stop；Game2/4旧本地ready门也未变。真实随机自动租约OS读回、rust原生5 UDP、共享reader routed≥5与最终Stop检查原样保留，未用人工PASS或跳过测试替代。

H1020 SOURCE需依次验证同一二进制原真实Linux双netns单自动IP所有者和三netns Alice/Bob两个真正原TLS账号A→A+B→B同时UDP，两个独立/32、单端口443、同Rust共享reader、可靠Stop；然后同源正常Normal/FEC/Game2/Game4和1%loss回归。任何下游FAIL按真正业务障碍处理，不能反向取消原生场景。历史H998物理MTU、ARM64 Game4FEC及Win/WSL2 Game4 lane2失效原样保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Repair actual original-Go native auto-IP readiness and Stop witness after H1019 normal-path false NOT_READY; retain strict real app and 3netns simultaneous evidence gate on newly locked SOURCE."}
```
