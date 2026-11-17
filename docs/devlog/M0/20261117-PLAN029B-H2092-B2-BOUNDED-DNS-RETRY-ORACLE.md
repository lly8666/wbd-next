# PLAN029B H2092｜真实 B2 四条 Windows 业务已过；Linux 上游重试验收过严

已复核签名[Action44060263345](https://github.com/lly8666/wbd-next/actions/runs/44060263345) 的原 ZIP `artifact14318238283`：SOURCE `071dde382a314d52fa2959201317b166b3f08677` 同源Windows2025签名Wintun/Npcap、原Go+Rust和WSL2 Linux，廉价/Go/Windows-Rust/Linux-Rust/对端构建皆PASS。原 Windows `client.log` 有实际`WBD_WINDOWS_CLIENT_READY`及`WBD_PLAN029B_V3_COLD_EFFECTIVE route_mode=2 business_split=true cn_domain_fakeip=false`。原物理客户端 `plan029b-b2-ordinary-windows.log` 明确**四个真实应用节点全部PASS**：CN独立物理DNS实际CNAME→海外A `203.0.113.77` TTL2、非CN通过Tunnel DNS得同一个海外A、两次该IP的真正Wintun→Linux TUN UDP业务有独立回包；普通CN无FakeIP写者。

**整个B2 Action仍FAIL、不得抢判PASS**：对应Linux guest脚本 `tools/m0_plan029b_b2_cn_guest.py` 的首故障在先前已经答过的某QNAME出现第二次同方向DNS上游UDP请求时立即抛 `B2 two upstream queries for one real app DNS ticket`，在最终4事件见证及双端Stop验收前终止。原029分流DNS契约§4允许同endpoint最多**两次**UDP尝试（仍不容忍跨方向回退），故此是比产品契约更严的纯验收条件，无法由现有日志断定产品不合格。

H2092只在同一Linux**测试服务端**放宽此一计数为**最多2次，所有尝试必须来自对应物理Windows源或原Tunnel lease，并保持所选单endpoint、准确QNAME/type/原问题；仍检查overseas真实A、真实CNAME/TTL，错方向、额外业务包、第三次UDP上游立即FAIL**。明确在最终报告记录各DNS出口`physical_attempts`和`upstream_ids`，不得把重试说成一次上游。产品Go/Rust、协议/TLS/AEAD/route、WAL/OS/Defender均原封不动。只按同一B2标记触发一次新SOURCE签名代表，若超过上限绝不再盲目放宽。

此前H2089 signed B0 [Action44056378053](https://github.com/lly8666/wbd-next/actions/runs/44056378053) 仍为旧SOURCE独立PASS_SCOPED；H2091的真实FAIL仍保留，B3/B4/B5未收口。未经真实owned Stop、完整Linux witness前，不能宣传B2或029B全部PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"H2092 only bounds Linux B2 signed fixture same-endpoint DNS UDP attempts to existing <=2 contract and reports actual counts; product feature behavior unchanged"}
```
