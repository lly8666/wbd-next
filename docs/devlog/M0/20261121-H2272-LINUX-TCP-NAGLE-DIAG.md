# H2272 · Linux TCP P99 的回显服务端 Nagle 单因素诊断

实验目的：H2270 原生 Linux 在 200ms 双向往返基线，真实 UDP 的 P50 约400ms，而小 TCP P50 约560–853ms；其 5% B TCP reverse-app P99约1795ms，server app处理仅0.074ms。已检视原回显测试客户端启用TCP_NODELAY，而服务端默认未启用。此处仅验证 Nagle+delayed ACK 是否扩大后向等待，不预设 Rust 产品逻辑错误。

使用现有 ARM64 三 netns、原 Go TLS/Rust、真实 Linux raw/TUN、同一原生构件、四条内核 TCP bulk 与160 TCP及UDP回显，每方向200ms且两端1%或5%真内核损伤。两个损伤档在独立 runner 并行；一个runner内服务端 A TCP_NODELAY=0 → B =1 → A′=0，逐次通过 OS getsockopt 真读回。原客户端TCP_NODELAY原来就是1，三阶段外层机会修复全部OFF；除此以外原数据面、MTU1160/1200、原FQ及Stop不变。双端Stop、接收有效吞吐、UDP未回、TCP前/后向P99和内层TCP_INFO均同源记录。旧H2270修复开关A OFF/B ON/A′ OFF不能与本Nagle单因素对照混用。

如果 B 降低 TCP P50、P99且不牺牲正常业务，应作为应用级时延机理证据而不是擅自对全用户TCP强设socket选项；如果不改善则更集中检查实际TCP loss/RTO、内核包损伤粒度及原Rust M4/RX排队。截止率与未回独立统计，160次回显仅限域。此 source 新测试尚 NOT_RUN，产品源码/配置/默认无变化。

\`\`\`feature-impact
{"kind":"none","reason":"H2272 isolates original Linux test-only TCP echo server Nagle in real original Go/Rust kernel-loss fixture; no product code, config, defaults, routes, ACK, auth or Stop changes."}
\`\`\`
