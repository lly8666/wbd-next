# PLAN029 H1827｜按用户优化建议调整Rust Direct调度与P2夹具

- 已收H1825真签名[Action43578369480](https://github.com/lly8666/wbd-next/actions/runs/43578369480)，SOURCE=0077dcb013045678e12761568a0dd58f35722704，V3原始Go/Rust真实Npcap/Wintun+WSL2，物理TCP1MiB 296ms、FakeIP Direct1MiB 6360ms、同SHA、半关闭、120/120 Tunnel小UDP、p99=15ms/最长31ms、双端owned Stop PASS。64KiB quantum源H1823物理281/Direct6141ms，TCP_NODELAY未实质改善；两次假设限域失败保留。新 evidence: docs/evidence/M0/PLAN029-H1827-H1825-NODELAY-P2-NEGATIVE-20261114.json。
- 本批Direct-only ingress每8个Wintun帧即使没有Tunnel也反馈捕获总量与Direct数，不再以Tunnel=0破坏drain/活跃判定。Direct TCP accepted/connect/实际read/write成功反馈给单Rust TX worker，可继续公平服务，不强行先等10ms；当各socket WouldBlock不计progress并恢复事件/现有定时等待。反向L3邮箱一轮8个满也作可能还有就绪的保守提示，不伪造递交计数。原Tunnel ACK和M2业务进度只按Tunnel封包，Direct不能续Tunnel payload idle。仍是有限轮/8flow、无逐流线程、无10→1ms空轮询；**独立共享socket完成事件/IOCP尚未实现**。
- P2夹具保持原真实socket基线与1MiB SHA，新增应用connect/upload/FIN/首回包/download的分段ms，并注明每16KiB有人为4ms停顿，不得当最大吞吐。保留首120次精确UDP收件，续发同一个Tunnel小UDP直到Direct TCP完整结束后由测试专用marker告知结束，Linux端最后一个有界UDP控制回显；同平台单调时钟核对UDP覆盖整个Direct TCP，另报sustained_total/p99/最长空洞。没有Go产品逐包泵或捕获文件写在热路径。
- **本批新SOURCE实网与队列/CPU效果NOT_RUN**，后续要核第一失败边界。按计划§4A紧接着修FakeIP同步persist_batch/sync_data阻塞TX、16MiB历史日志压缩、真实VecDeque retained capacity记账/低频回收；P1+7.42%的绝对0.009核需进一步归因。正式Normal无CI gate、Game4 CN、GUI实际Connect/Stop、IPv6/其余029出口也未关闭。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Direct-only work/relay progress scheduling and P2 sustained whole-transfer measurement; verified H1825 negative performance result without promoting feature."}
```
