# PLAN029 H1836｜只发一场真签名P2观察Direct调度修复后分腿时间/全程Tunnel小UDP

- 已有H1825原真P2在SOURCE0077dcb双腿TCP_NODELAY后物理1MiB 296ms、Direct 6360ms，120/120旧短UDP与Stop PASS（性能仍OPEN）；H1827`StageWork{tunnel,captured,direct}`＋TCP accept/connect/read/write进展反馈和H1828保留容量账本已写、Linux/Windows纯组件PASS但**此新调度SOURCE尚未有签名1MiB性能验收**。不再复测旧量子或Nagle参数，要求初次新的机制证据。
- H1835刚提交正式分流CLI/GUI配置与source-current WinForms/真实Go校验，GUI Action43587702812仍在单独跑**不带网络**，可与本Action不同Windows宿主并行，严格不同场景/不共享VM。
- H1836只加短devlog/cursor，冻结SOURCE后用已授权、现存`[plan029-v3-real-p2-rebuild]`标记派发**一次** Windows2025签名Npcap+Wintun、Ubuntu WSL2真核P2：同VM正常物理socket基线→FakeIP Direct TCP 1MiB按源锁相同16KiB块＋每块人为4ms发送间隔；客户端`connect_ms`、`upload_ms`、`half_close_ms`、`first_reply_wait_ms`、`download_ms`与总耗时拆开报告（此夹具非峰值吞吐）；Tunnel小UDP在直连TCP启动前持续到真正完成，记录`sustained_total>=120`、唯一序号、p99 RTT、最长空洞、两个实际出口、两端owned Stop。阶段时间可证明等在哪段但不能冒充每腿内核事件时序/独立CPU/RSS。
- 本提交时H1836真签名P2实际耗时、TCP改善、完整UDP/p99/RSS/队列年龄均**NOT_RUN**，必须收Action结果才更新结果与功能卡，不把"绿色编译"写成性能PASS。若原生P2首个产品业务失败，留失败并只修第一边界；不重复dispatch、不恢复028矩阵。
- P1纯TunnelCPU、D4 IPv6/Stop中断、Game4 CN、GUI真实Connect Stop、FakeIP慢磁盘/日志压缩真实恢复、必要共享socket事件与Direct低延迟依旧OPEN；029仍IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Source-frozen doc and one existing signed mixed P2 scenario trigger only, no code/GUI/protocol change; freeze performance claims until actual new-source results."}
```
