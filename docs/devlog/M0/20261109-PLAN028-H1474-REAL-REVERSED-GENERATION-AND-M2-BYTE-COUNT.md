# PLAN028 H1474 — 真实五客户端正反序原始换代实验、与换代时数据是否翻倍

SOURCE固定 `66fb6b4454b1ce4297ab04efa20c7f931ff12383`。H1472 [离线Action42595376932](https://github.com/lly8666/wbd-next/actions/runs/42595376932) 复审旧八场真正五客户端各180s原始四ZIP成功：五场严门PASS_SCOPED、三场FAIL_SCOPED。原始native Action红色发生在全部真实业务和六个owned Stop结束后，因Python错误嵌套路径而非八场全产品失败。

H1473 [原生Action42595013191](https://github.com/lly8666/wbd-next/actions/runs/42595013191) **同一台x86 Runner连续真实五客户端两场180s**、同一SOURCE Go/Rust/ISA-L机器码，以`rotating12→static12`倒序。原始[artifact13663646307](https://github.com/lly8666/wbd-next/actions/runs/42595013191/artifacts/13663646307) ZIP 75文件 CRC_PASS。第一场轮换：原五用户M4合法换代、六进程Stop PASS_SCOPED，但Alice真实下行少13、Carol真实下行少3，server五租约queue overflow0；第二场无换代五用户十方向零缺包、server queue0。先前H1467正序 `static12→rotating12` 也是静态零缺包、换代实际25个下行缺（Alice16 Bob4 Carol4 Erin1），队列0。同源、同规格VM正反序强化换代边界相关性，**仍不能在没有逐包时间戳的情况下把M4交接本身判为唯一第一丢点**。

“换代是否应两倍流量”：原源码Go `path_supervisor_linux.go` 只允许一个CURRENT、一个candidate和一个retiring；共同使用单个Rust共享TUN reader，M4真实认证之后只把默认TX路由交给新代、旧代约10–20秒保留authenticated RX+旧RAW在途包，后精确Stop。多两代并存意味着资源/握手/接收额外开销，**不意味着内层业务始终复制两份发向两个generation**。H1473原始Alice每个generation独立M2 `first_wire_bytes` 求和：轮换3代合计294,216,166字节，静态单代294,143,551字节，相差72,615字节，即+0.0247%左右，双方`repair_accepted_wire_bytes`和`original_frozen_retransmitted`均0。这是**整场180s累计**，不是每10ms瞬时上限，不能证明重叠窗口没有CPU峰值/重复个别包；但反对“每次换代持续两倍业务带宽导致12Mbps丢包”的解释。

下一次只做低成本、短时、逐generation边界观测，记录 M4 ready 之前/之后原server M1出站拷贝和RAW内核TX、原client RAW RX/原Rust M3交付、对齐业务UDP packet ID与100ms时间窗、Old owner Grace结束，区分在server发送前丢包、RAW接收前丢包和接收后M3重放/路由失效。另一个高压75Mbps间歇性server队列Full的故障域独立处理，不用同一个补丁掩盖两个问题。原Source66fb 600s高压32缺/queue45，1800s低压轮换351缺/queue0严格FAIL均保留，Windows正式1800 NOT_QUALIFIED、H998历史HOT FAIL、Android/物理NOT_RUN，PLAN028继续IN_PROGRESS，无PLAN029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"New original reverse-order five-client native artifact evidence and exact cumulative M2 byte accounting; no network, crypto, protocol or product change."}
```
