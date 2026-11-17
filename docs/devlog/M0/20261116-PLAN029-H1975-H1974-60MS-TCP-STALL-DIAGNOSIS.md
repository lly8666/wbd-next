# PLAN029 H1975｜拒绝将失败原生Action误报性能PASS，优先真实60ms异常

- 原SOURCE `bd611192c397220d467a8330defce4e0d494ac04`，[Action 43808776053](https://github.com/lly8666/wbd-next/actions/runs/43808776053)，job **133107537568** 最终**failure**于第19步原两系统业务，artifact **14199838286**，原报告 `normal_public=FAIL_TRUE_PUBLIC_EXECUTION`、`error=H1966 QPC: missing or ambiguous request-to-owner QPC joins`。
- 同一SOURCE Windows2025原Go/Rust/Wintun↔WSL2真Linux kernel TCP46119，Windows物理和Direct各**2048条1KiB+32预热**，真实每臂2,129,920字节SHA `0c5cfc1733c1b0e54b53e2b67a1777dc4f7d27a0e77669f625aa8d8af40fa927`、FIN和双端 **owned Stop PASS**。这只是业务真数据核对，不是QPC性能完整PASS。
- 原Rust Stop显示新签名同轮交付实际 `delivered=5610 max_per_turn=8`，故代码确有执行；普通产品此优化开关OFF。原Wintun入站QPC **2084条**（应为2080=32+2048）、原kernel relay读写QPC **4160条**、两个drop=0。多出四条是相同TCP源port和seq、payload1024字节真实重传，seq为 `3389418656`、`3389674656`、`3390468256`、`3390470304`；原分析器严谨校验每窗口正好1024B而拒绝2x1024B，原Action应保持FAIL，不得剔除样本伪造PASS。
- 本源物理p50/p99 **217/356μs**、Direct **473/741μs**，单次同VM物理/Direct差p50约256μs、p99约385μs；旧H1970物理95μs，**不同虚拟机物理基线本身慢2倍多，跨run绝不能宣称优化因果**。没有证据让代码转产品默认。
- 五次真实Direct请求RTT约 **61.270、62.696、61.219、61.404、61.441毫秒**（原2048测试0基索引 **865、920、1170、1945、1947**）。第一份TCP数据进入`on_packet`/NAT后，inner原kernel TCP socket在约60ms后才被真正读到。其中四次有原序列重传，另外一次完全无重传；第920及1945次的**原inner读取比重传Wintun再次入站更早**，因此严禁误判“重传引起等待”。
- 真正未定位的大项：首次NAT已入列→实际RX Wintun `SendPacket`成功→Windows kernel TCP accept/FD_READ→原Rust inner read之间究竟哪一段耗掉约60ms。要在**原唯一TX/RX worker**上增加有限、源锁、同Windows QPC 的端口/seq/字节时间戳，收集真实第1包与重复包；不能假定队列`try_send`即等于内核已收。原20–50微秒正常抖动和分类器亚微秒在此任务优先级下降，不继续极端CDN同IP。
- 下一步只有当原日志明确定位确切未唤醒阶段，才考虑原事件驱动的**一次有界补救**；不加独立读线程/重复Wintun/猜想TCP ACK，不放松SHA/FIN/Stop。保留完整PLAN029 IN_PROGRESS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record real H1974 failed original QPC byte join caused by four genuine TCP retransmits and five 61ms Direct-only kernel-read gaps; preserve genuine app SHA/FIN/Stop as scoped partial evidence without promoting product or performance."}
```
