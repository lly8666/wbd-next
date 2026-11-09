# PLAN028 H1485｜真实ARM64双代验真归档；x86 Game4旧READY标记引起早退（业务尾段未测）

原始 [Action42630288439](https://github.com/lly8666/wbd-next/actions/runs/42630288439) SOURCE `57b0d0cded995cf26b6f8ea43a3d4588e6e61d27`，真实原生 ARM64 双端，同一443 Normal/Game2/4、五客户端180s、Go/Rust装配+L0 +固定原生manifest TRUE PASS。原artifact13680553258 ZIP SHA256 `a38cdc13da3bf984c08ab3d8d82d31a322910926e31c86c01360ea4ffc6dd6f1` CRC PASS，原 `h1480-ready-verdict.json`：Normal server B deferred/Health promoted/Go ready 均6，Game2 server B 均2，Alice/Carol各两次客户端真正认证提升，五用户十个UDP方向全 0 unique missing、全部六个 owned Stop、Server shared TUN overflow/retired/age 0。定性 **PASS_SCOPED_TRIGGERED_SERVER_B_READY_AND_ZERO_UNIQUE_UDP_LOSS**，不是全PLAN028完成。保留原 H1483 Carol DL 5 真FAIL。

另原生 x86 [Action42630288111](https://github.com/lly8666/wbd-next/actions/runs/42630288111)、原artifact13679959152 ZIP SHA256 `1228dbeea002869c1a9f94fa17324174e330f1a758bb3236ad4552079a23778a` CRC PASS：真实 Game4 整组 B TLS/M4和client Gen2 READY，server B TUN deferred→client已认证Health→TUN promoted→Go B_CLIENT_READY，旧A 10–20s精确Stop，物理 source `10.25.0.3` 已读回。**旧夹具仍要求 server `V4_PUBLIC_GAME_MULTI_GROUP_READY` 出现两次**；H1484修复将第二次改成新authenticated-B事件而不提前声明本地READY，因而原脚本在实际五次新路径UDP之前就报 `PATH_SWITCH_NOT_READY`。不得把 Action FAIL解释为新路径UDP真丢失：其 UDP 尾段应为 **NOT_RUN**。已比对历史 x86 PASS 与当前 FAIL 原始日志，不盲刷同seed。

本次只修原 shell fixture 的 ready 条件：历史两次本地READY兼容；新语义要求同一server B `V4_PUBLIC_GAME_SERVER_B_CLIENT_READY` + `V4_PUBLIC_GAME_SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX`，所有其它条件（client Gen2、原路由读回、双方old exact Stop、内层MTU、真正5次UDP、8个真实TLS ClientHello）保持硬门；修复Rust L0 test-only重复 cfg/test 属性，避免把相邻Normal测试的Linux门丢掉。重测只在新独立H1485 x86 Action加载**同一原SOURCE57b** 既有Action42630288111固定3 ELF hash与manifest，绝不另建产品 SOURCE；与原FAILED artifact严格分开记录，原业务尾段仍未验。

并行自动触发原H1151 x86与H1157 ARM 单端口混合共存已 PASS；另H1200短 Game2 first-live旧历史断言 FAIL 独立保留，未因别项PASS收口。Windows 真实1800、Android/物理留未跑，H998 MTU及历史600/1800损包原样保留。PLAN028 **IN_PROGRESS**。

```feature-impact
{"kind":"none","ids":[],"reason":"Evidence reconciliation and fixture-only acceptance repair, reuse immutable original Go/Rust binary; no production or wire modifications."}
```
