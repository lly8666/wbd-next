# PLAN029 H1977｜优先拆解真实 61ms Direct 卡顿，不做小差异优化

## 唯一问题与原证据
H1974 [真实 Windows2025/WSL2 Action43808776053](https://github.com/lly8666/wbd-next/actions/runs/43808776053)，SOURCE `bd611192c397220d467a8330defce4e0d494ac04`，**原原生 Action FAIL**（4个同序号TCP重传使严格2048窗口QPC检验FAIL）；真实Windows与Linux各2048×1KiB+32预热、SHA、FIN及两端owned Stop PASS。五个Direct请求出现**61–63ms** RTT，其中首次Wintun `on_packet` NAT入队仅~0.03ms，至原inner WinSock `recv` 正向读到约60ms。此延迟比常见分类/NAT p99~1μs明显几个数量级；不再优化小项或极端CN/CDN同IP。

## H1977只增加签名QPC观察，不更改产品调度
- 唯一真实TX owner中，在**原 channel`try_send`成功**处记录源锁Windows QPC：`proxy-port:原application-source-port:seq:1024:before:after`。保留旧32条优先队列与H1972 signed-only 8条同轮队列，不能凭`try_send`声称 Wintun 已注入。
- 唯一真实RX owner中，在**原 `WintunTx::deliver_native_direct_response`调用前及成功返回后**记录`proxy:0:seq:1024:before:after`，沿用原严格内核有效性校验、Wintun唯一写owner和满环TCP FIFO重试。成功返回代表 **`WintunSendPacket`调用已完成**，不代表原Windows TCP内核收到了，更不是ACK。
- 原 WinSock `WSAEnumNetworkEvents`仅在`FD_READ`确实出现时记录 QPC 的`原port:inner/outer leg:observed-now`。它是**Rust观测WinSock就绪通知的时间**，不是不可见的内核事件真正发生时刻。原`NativeTcpActor`签名Stop输出仅一组`proxy→source-port`映射，防止把NAT重写后的源端口和原Windows应用源端口混成一个。
- 只在原`m0_v4_probe+GITHUB_ACTIONS+WBD_PLAN029_NATIVE_V3_TRIAL+P2_MIXED+P2_STEADY_QPC+P2_BOUNDARY_QPC`全部符合时，每条已验证1024B完整TCP DATA添加QPC；两owner各**最多8192行**，超限计数并拒绝伪造，无每包stdout、无第二Wintun、Go回调、WFP、独立线程、按包内存分配，普通用户路径OFF。
- `tools/m0_plan029_h1977_boundary_qpc.py`按原app2048窗口+源port/代理port/TCP序列/同Windows QPC联合，**重复TCP报文不丢弃**，保留严重>=8ms窗口的NAT→TX、TX→RX送出前、Wintun send调用、Wintun提交→inner TCP recv及FD_READ记录，独立`plan029-h1977-boundary-qpc.json` sidecar。原H1966严格一窗1024B检验仍在，遇到同序号TCP重传可以**继续FAIL**，不拿诊断报告伪造性能PASS。侧证文件仅在原双方Stop后创建，Linux时钟不和Windows QPC相减。
- 源码初始提交**不带任何昂贵原生scene触发词**。先收H1977 Python合成负例、Rust Windows/Linux组件、Go装配及Governance/Feature；通过再以同SOURCE签名提交唯一正常流2048×1KiB Win2025/WSL2测试（若复现60ms也明确保留FAIL）。如Stage显示Windows已收包但inner recv延迟，才试一次明确的事件/唤醒修复，而不是一边补采样一边擅自打开同步轮询。

## 验收边界
原 H1974 signed 同轮交付 `delivered=5610` 只证明此路径执行，**未证明性能提升**且普通产品OFF。H1977未实测之前不得报任何新 p50/p95/p99。CN/非CN同真实CDN-IP极端工况按用户指示不优先，完整PLAN029 D1–D5/P1–P2/GUI/Game4/IPv6继续 `IN_PROGRESS`。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add bounded signed-only 1024B original TX mailbox enqueue, RX Wintun SendPacket return and WinSock FD_READ QPC plus source-locked retransmit-preserving diagnostic sidecar for genuine H1974 60ms stalls; product runtime unchanged and native NOT_RUN."}
```
