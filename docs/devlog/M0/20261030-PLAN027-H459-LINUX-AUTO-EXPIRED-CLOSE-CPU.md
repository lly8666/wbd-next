# PLAN027 H459｜真实 Auto 42秒单核空转的截止时间前提修复

H455 B Auto真实Windows↔Linux Action40994443303/artifact12951230045：Windows发385、收到0；Linux发100、收到27，双方Ready。Linux原Go/Rust服务端RX曾正确认证收到466源并完成TUN，但M4 TX只读入10，FEC源提交9，部分封块规划r7 sent0，TX线程CPU41.8039158s/约42秒墙钟。**这是生产首到与CPU退化**，不能仅列质量UNKNOWN或移除送达测试。

LinuxQualityTx `due()`/`next_signal()`已经阻止START后未曾收到PN>=first时CLOSE，但Rust同TX worker `low_close` 直接对sender调用 `timed_close_deadline()`，在无新首发时变成永久过期的earliest和0ms轮询，导致CPU饥饿并丢业务。新增只读 `next_close_deadline()` 绑定真实 `last_settled>=sender.key.first` 与sender timed deadline，TX deadline聚合统一使用。已有开始/完成真实1024PN的单测扩展成无新DATA 9s也无 due/deadline，收到一份真实DATA后才允许限时CLOSE。Health仍独立、Idle仍UNKNOWN，M3原密文/PN、Stop、MTU、FEC分组均不动。

原失败 run/job、server TX CPU 41.8/42s、真实 app counters原样保留。H459源码未测试，必须新SOURCE Linux/Windows两端Auto复验真实TUN、业务第一到达、p99、CPU与Stop，不从A1/短样本造PASS。A2/A3和B Fixed已有source复用Actions在途，不重复dispatch。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Prevent real Linux Auto TX 0ms deadline spin after START without in-window DATA; first-delivery/CPU regression pending same-source Actions."}
```
