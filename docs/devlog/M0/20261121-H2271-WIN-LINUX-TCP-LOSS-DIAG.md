# H2271 · Windows/Linux 1%/5% 200ms TCP 首段真实归因（2026-11-21）

用户授权在 PLAN029 内优先诊断双端 1%/5% TCP goodput 与 P99、尽量复用并行原有 Action。继续已登记实验分支与 Draft PR#68，原 main 游标 H2245 过时；本文件是 WIP intent 与实验范围，不是新产品 PASS。

**已确认**：Linux H2270 原 Go TLS/Rust ARM 原生 4 bulk TCP +160 TCP/UDP、双向200ms，1%/5% ON 的真实原密文 R/F=1.09%/4.19%，但 TCP 61.32/23.69Mbps，小TCP存活P99 727/1996ms；同场 client SharedTun满丢0，因此不能用无损高供给 H2261 的 SharedTun 溢出直接解释本场。5% RTO 和高 RTT 仍待逐段归因。Windows H2269 1%/5% Actions44916725571/44916727879 只是双向 10Mbps 以 UDP 为主的 source-locked 场景，实收约9.9/9.5Mbps；既非 Windows 四TCP上限，也没有 OS TCP P99 结论。两组 Action SOURCE 不同，不能跨 VM CPU 直接因果比较。

**H2271 单增量**：在现有 Windows2025 signed NPF/Wintun ↔ WSL2 Linux 原Go TLS/Rust、双向 tc netem 已开启、原60s UDP源锁计量完成且 owned Stop 尚未发生时，增加顺序独立 TCP 子窗口：Windows Wintun/32 发往 Linux TUN、以及 Linux TUN 发往 Windows Wintun，各四个真实持续内核 TCP bulk 与独立160次16B真实 TCP echo，同一端本地单调钟求 P50/P95/P99、>1s/>2s、实际对端接收字节/总时长及错过回复；独立验证双方内核监听 IP 与源 IP、回声顺序。诊断应用最多四个有限客户端线程/连接和一个回显，老业务二进制、司机、Go/Rust、WAL及默认参数不动。单场按丢包1%/5%各自 Action并行，单 runner保持 OFF→ON 顺序；不要混合两loss种子或冒称两个独立 runner的CPU因果。

**下一判别**：首先是否可复现 Win TCP 低吞吐/高尾；若未复现，不能按用户担忧直接修改 Win 缓冲。若复现，先比较同场 Windows源与Linux源、TCP echo P99 与 TCP_INFO/Windows TCP RTO/Wintun/Npcap真实 drop，再设同MSS direct baseline，分开本机 full、内层 TCP丢段与WAN下游丢包。H2270 的 R>0仅证明原密文重传，不证明原TCP及时抵达。需要改变条件时保留回退基线和未回分母；不可为了减少尾时延人为饿死 bulk。没有新根因不得重跑 H2263–H2266 已否决参数系列。

**验证边界**：此提交测试夹具及Workflow预检，产品源码不变；新 1%/5% Win+Linux 真实 TCP/CPU/P99/两端Stop NOT_RUN，待原生 run/attempt/artifact 与实际源 SHA 收取后判断。不能从异平台成绩继承 PASS。

```feature-impact
{"kind":"none","reason":"H2271 adds original signed two-OS native TCP loss probe in existing Windows runner only; no production Go/Rust, configuration, defaults, protocol or Stop behavior change."}
```
