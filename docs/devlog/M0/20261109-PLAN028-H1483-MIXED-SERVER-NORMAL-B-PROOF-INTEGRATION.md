# PLAN028 H1483｜H1480真实ARM64失败暴露混合Normal/Game服务端漏接认证B就绪

[真实Action42624321547](https://github.com/lly8666/wbd-next/actions/runs/42624321547) SOURCE `cea267bd4c9b2323a19093308401580fe3123605`，原始 [artifact13677857794](https://github.com/lly8666/wbd-next/actions/runs/42624321547/artifacts/13677857794) ZIP SHA256 `ca1190721dd2c47a3cf3ad8fe69fe19fb3e7f3f08d785983fd0606167b942568` CRC_PASS。全部Go+Rust原生ARM64双端build/manifest/ISA-L与Go/Rust L0均PASS，真实5客户端180s mixed normal/game/TCP+UDP 0损伤、six owned Stop真完成。**业务严重FAIL**：Alice DL129677、Bob DL22480、Carol DL1、Erin DL31012，总183170真实唯一UDP缺失，UL全部零缺；server Rust `V4_PUBLIC_NORMAL_TUN_CANDIDATE_DEFERRED role=server`=3，`...SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX`=0，client Alice新两代真实M4 promoted=2。无容量/报表赦免。

定向复核源码与原日志：真实混合 Normal/Game 单端口五client入口调用 [game_linux.go](https://github.com/lly8666/wbd-next/blob/main/r0/go_overlay/internal/v4productcli/game_linux.go) 中 `runOriginalGameMultiServer` 的 `case authenticated` Normal 分支。原 H1480 只改了 [linux.go](https://github.com/lly8666/wbd-next/blob/main/r0/go_overlay/internal/v4productcli/linux.go) 普通多session服务端 B Health proof；Rust公共 `shared_route_defer_live_replacement` 同时作用于混合server，但其Go尚按old 10–20s grace直接把新 B 写入 `activeNormal`、定时Stop旧A，**没有调用** `PromoteNormalServerAfterAuthenticatedPeerRx`。故A被停止、B仍未获唯一/32 TX路由，长时间下行丢失。该原始严重FAIL保留，候选未通过。

本批最小真实修正：沿当前完整线 `normalPending[key]` 保存未接管的已真实TLS/M4认证B，仅在同principal/tunnel一份B可pending；其原生server M4已有Rust挂起而A仍唯一负责发送。一条cold-only有界5s proof goroutine调用已有 `waitOriginalNativeServerClientM4Ready`、只读新B认证M4 `AuthenticatedPeerControl`，向**同一个混合接入select**投递结果，无阻塞event-loop等Health或抢健康兄弟。单线程接入Loop匹配exact pending token后调用已有 `product.PromoteNormalServerAfterAuthenticatedPeerRx()`，成功才发布 `activeNormal[key]`、排旧A grace/精确Stop；失败/timeout只撤B/其元组+native Stop，不伤A或Game。初代无A保持立即发布；最终Stop先join所有cold proof，再精确Stop未证B/已活各组。无新增稳态wire/业务双发/Go热搬运/第二controller，唯一用户模式/MTU不变。

H1480 strict native verifier 之前仅识别普通 `V4_PUBLIC_MULTI_SERVER_B_CLIENT_READY`；同步承认**真实混合Go proof** `V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY`，分别报告两路径计数并要求实际两次授权与零unique下行/上行；不能用纯静态无触发PASS关条件修复。该新SOURCE尚无实测，请按ARM native新SOURCE同一完整一Action验证；当前PLAN028 IN_PROGRESS，原证据与全部未验限制保留。其它25 push触发的历史workflow无关本场，不能冒充本轮通过。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct already authorized PLAN028 cold authenticated server B route promotion in actual mixed Normal/Game listener; no new protocol/config/GUI."}
```
