# PLAN029 H1860｜独立4MiB未限速Direct/Tunnel场景；保留H1859 P1在途

- H1856真签名P2 1MiB人工16KiB+4ms节奏 Direct 328ms/物理281ms、Tunnel UDP120/120、owned Stop PASS_SCOPED；此为功能和低负载延迟，不代表峰值/CPU/GiB。H1858 `13312046` 4MiB bulk只编译，原native SKIPPED；**P2 bulk并未执行**。H1859 `ef46a846` 已针对P1 B缺V3 DLL export和bulk入口漏marker修正builder/MTU/scope；H1859独立P1 Action仍在途，本提交绝不触发P1第二次。
- 本SOURCE只触发已授权的 `[plan029-v3-real-p2-bulk]`：同VM先普通物理WinSock 4MiB unpaced，再真实signed Wintun→Rust Direct TCP 4MiB unpaced，同时原Tunnel小UDP持续整段；P2子进程用明确第4个argv标记将4MiB条件传入WSL2客体，避免不同负载的伪AB。SHA、TCP半关闭、120+不同序号Tunnel UDP、p99/最长空洞和双端owned Stop均保留真实oracle；原1MiB paced选项不变。未引入Go热泵、第二TCP栈或旧WFP。
- 额外补充测试对4MiB负载和跨WSL参数传递的源码守卫；H1858 FakeIP journal compact重编码已移入原有1个有界磁盘worker，Windows/Linux纯测PASS，本场不会冒充慢盘压力验收。
- 修正上批H1859功能卡有实际变动却误报`feature-impact=none`的声明为`updated`；不改治理上限/历史负证据。H1860真实交付与P1结果此时**NOT_RUN/IN_PROGRESS**，029仍未收口。

```feature-impact
{"kind":"none","ids":[],"reason":"H1860 changes only additional native P2 bulk fixture guard and restores truthful previous H1859 feature-impact metadata; card and product behavior unchanged."}
```
