# PLAN029 H1716｜收H1715真实源码门，构建唯一Rust Direct UDP flow/socket actor

H1715 SOURCE `f1dc2cd0c6e8e36734967abb434f40a6528d417f` [Windows original-Go source/PLAN029 build](https://github.com/lly8666/wbd-next/actions/runs/43374768091) SUCCESS; [M0 PLAN020 Windows WAL](https://github.com/lly8666/wbd-next/actions/runs/43374768163) Go build＋Normal/Fixed/Auto/Game2/Game4原TLS signed Wintun局部场景成功，原日志 `host_global_WFP_NOT_RUN`、`os_applied=0`，**不是新029分流/四阶段OS本代产品 Applied**。Governance+Feature catalog SUCCESS。M0-WIN-LINUX native-public-two-os 此时尚在途，保留原结果待收，不派重复场景。

新 `crates/wbd-engine/src/v4_client_direct_udp_actor.rs` 仍是待CI的Direct UDP产品组件：一Rust代际 actor 每原应用五元组一个真实绑定物理源IPv4＋ifindex的nonblocking WinSock socket，严格保存原展示目的和真实remote，源租约校验；普通UDP/53必须交QNAME Resolver，FakePool地址不得外发，socket满额仅报本Direct flow失败、绝不改走Tunnel。WSAPoll零超时就绪列表仅在flow增删时重建，每次最多64回复量子，反向IPv4/UDP包先备齐再交未来唯一WintunTx；粗tick分批检查到期≤1024flow，无perflow线程/Go per-packet pump/新Wintun reader。只是代码，**未连已有唯一NativeOwner stage_sources和原Rust rx_loop**，16k上限只是内存/流条目上界，实际内核socket内存、CPU/PPS/RSS和全局64MiB仍需实测，不报性能PASS。

原 H1713 Wintun→直连DNS CNAME/A→durable FakeIP→Linux guest原app UDP回程、H1709内核TCP→Linux guest/Windows真实FIN以及H1697真实no-WFP四阶段OS各自局部正例保留，不升级为029全验收。需继续唯一Rust TX/RX装配、两个单DNS出口及config/GUI/start padding/Normal+Game4/D1-D5/P1-P2；028/030不动。

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Collect source-locked H1715 original-Go no-old-WFP admission build PASS and stage one-generation Rust physically bound UDP flow/WSAPoll actor for future original NativeOwner only; no product Ready."}
```
