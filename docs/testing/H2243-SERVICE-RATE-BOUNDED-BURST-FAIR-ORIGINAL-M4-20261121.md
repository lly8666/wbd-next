# H2243｜原生统一流控：公平反馈必须保留 M4 原同步批量服务

**M0 独立测试 Draft，非产品默认变更。** H2242 已验证控制 Rust/TUN 两层损失具备可行方向，但同源跨双 ISA 发现 CAKE 每包匀速发送导致真正原始 M4 每次 sendmmsg 由14–17包坍缩为2–4包；即便下层丢包接近零，CPU/交付GiB恶化70–100%，接收goodput下降。此发现比“调优CPU”更具体，是**公平入口时间粒度与原M4 batch服务粒度冲突**。

## 已验证的起点

[H2242 Action 44852383940](https://github.com/lly8666/wbd-next/actions/runs/44852383940), SOURCE `b6a64a19e4984b9ac3da701672063a4cb4d0b458`，两架构各自4/4 WBD真实TCP与原Go TLS/Rust-owned Stop成功；最终独立Direct iperf控制socket双方都FAIL，故整个Action FAIL，不冒充双基线稳定。x86原始 fq600/流 接收278.5/320.0Mbps、M4每batch14包；CAKE450总公平242.3/271.2Mbps、每batch2.9/3.6包，Rust本地满队列81,076→29,090→1,702，TUN link丢包仅0/6、qdisc 4/3。ARM原始357.7/364.4Mbps、每batch16–17；CAKE296.8/299.1、每batch2.4、Rust满队列25454→910→14、TUN link 0/0，CPU/GiB从10左右增加至17–18。CAKE固定450限速本身绝不等价于正当动态产品默认。

## 下一刀：公平的可控聚合速率，但不破坏 M4 批量同步发送

单个VM三原生Linux netns/Go TLS 1.3/Rust TUN AF_PACKET/真BBR TCP，GE目标1%额外单程200ms、四条TCP流，每架构独立同机4个原始客户端generation：

- A: 原产品创建 `fq maxrate 600Mbit flow_limit256`（注意**每flow而非整TUN**），原 Rust reader 不暂停。
- B: **只在当前客户端自己拥有的 `wbdc0` 测试用** `tc root handle1: tbf rate450mbit burst16kb latency15ms` + `parent1:1 handle10: fq_codel limit256 target5ms interval100ms ecn`；TBF对整TUN token-bucket有界发burst，fq_codel维护五元组公平与有界小队列、ECN标记；仍然**不暂停Rust reader**。
- C: 同样TBF450和fq_codel，但burst48kb。16KiB≈原M4约14个内层MTU packet的量级，48KiB是对照长批并用于识别内核隐蔽积压风险；不能拿48KiB当默认。
- A': 新原始Go客户端generation再次恢复原 fq600/流。测试前后真Direct容量守卫；H2242最后Direct控制socket关闭，故H2243只对**自己启动并PID验证拥有的临时iperf direct listener**执行一次正常退场重建/读回，再做最后一次参考；**不重试失败场景、不刷GE seed**。

保持原Rust原SharedTun每路8包/64KiB/100ms、M4 64槽同owner、TUN内核txqueuelen2048、原设备/用户配置均不改。双ISA x86/ARM各自同源连续A/B/C/A，绝不跨VM计算CPU提升；Ubuntu24.04 GE缺seed，不能说每个业务字节遭受相同丢包。

每阶段须量测**真正接收端goodput与iperf3内层TCP重传、实际内核TUN link tx_dropped、TC TBF根和fq_codel子层packet/byte/drop分开存、Rust SharedTun queue-full/age/byte/200ms尾、原M4 copied/batches及CPU/实际GiB、owned Stop、源与run-ID**。TBF和子qdisc统计可能重叠，不能简单相加得丢包总和；要从各层分类，尤其绝不把缺失统计转为0。若 TBF限制输出很均匀而批量仍只有2–4、或者Rust queue-full只是变成fq_codel丢包/队列age↑/TCP tail p99变差，判FAIL并据此改正**当前原服务路径的吞吐反馈节奏**，不能改第二套外层可靠重传。

## 完整产品设计出口

如果B/C真的把本地多层drop都合理压低且恢复M4批次、实际goodput/CPU/GiB不差于A/A'，只证明**方向**有益。正式产品不能固定450Mbps、要求每包tc reconfigure、提高队列或长期Hold DATA；应在现有唯一Rust native owner的**实际同步sendmmsg完成回执**基础上，以低频/有界/逐租约独立的能力估计决定原生入口公平放行；接入点不得变成第二稳态controller或Go逐包FFI，不得通过等待缺少的PN/FEC/旧业务完成让新业务排队，跨租约、跨flow公平、实时small TCP/UDP p99、Stop、Windows和Linux ARM及Normal Fixed/Auto/Game2/4完整验证后才能推广。

**不可突破**：Go标准TLS、TCP-like ACK/Window外观、乱序首到立即交付、无跨业务HOL、原Rust唯一热数据owner、仅表演式/机会式有限原密文同PN外层重传、FEC独立截止、AEAD/认证/lease/generation/MTU真实保障。此工作仅内核局部试验，不触碰主线或别的活动作者。
