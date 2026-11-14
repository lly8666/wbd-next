# PLAN029 H1852｜Npcap 原读取移交后未设置非阻塞：首RX阻塞边界

- 收回 [H1851签名P2 Action43605289460](https://github.com/lly8666/wbd-next/actions/runs/43605289460)：Windows/Linux预检、真实Windows Wintun与WSL2准备均执行；Direct 1MiB 上传18.969s、到38s仍仅917504B回显，业务Stop NOT_RUN；仅精确owned finally清理分别PASS。已有ready峰32/256，ready_full=0，**32/32量子没有解决P2**。
- 另一个审查意见指出更靠前的可能共同首边界：Go Npcap原句柄50ms blocking `pcap_next_ex`，交Rust时只`gate.close`/`gate.wait`、`pcap_getevent`，并未显式切非阻塞；Rust RX虽然先处理Direct返回，但在NPF event后连续最多32次`pcap_next_ex`，某次等待未来包即可拖住下一轮Direct ACK/window/DATA回注。Npcap官方文档明确默认捕获为blocking，必须`pcap_setnonblock`才能保证空读即时返回0。32×14ms只是风险上界示意，**不是已经测得的448ms**。
- 本SOURCE仅在**Go所有原reader完全退出之后、Rust借用前**为这一个原captured `pcap_t` 调用`pcap_setnonblock(handle,1)`并读回`pcap_getnonblock(handle)==1`；函数缺失/失败则保留旧gate关闭语义、精确回收自己已关闭的该endpoint和DLL，不借出未知阻塞句柄。原`pcap_getevent`/WaitForMultipleObjects空闲事件等待和原TX句柄不变，无忙轮询、不扩线程，不动WFP。
- Go Windows纯测试覆盖set/get状态拒绝。真实效果必须同SOURCE签名Normal P2原1MiB＋持续Tunnel小UDP复测，收1Hz四腿、ready峰及实际交付；测量前只算**IMPLEMENTED_UNVERIFIED**，不把单Action绿当低延迟合格。
- 此次不提交此前尚未发送的“无UDP/有UDP”双阶段夹具，以避免多个变量和额外网络场景；继续保持H1850/H1851负结果与Game4/GUI/IPv6/P1/D1–D5残项OPEN。
- 修正治理M0 cursor context_refs从10项压回仓库现有8项上限；旧文档/evidence留在仓库，不更改治理准则。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Capture actual H1851 P2 FAIL and fix missing cold Npcap nonblocking handshake so Rust RX batch cannot wait for future NPF frames; no verified P2 performance claim."}
```
