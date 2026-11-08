# PLAN028 H1361｜ARM64 原生单向弱网业务验证

- [H1361 原生 ARM64 Action](https://github.com/lly8666/wbd-next/actions/runs/42442284471) 两个 Job SUCCESS；SOURCE `24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73`，原始 Go TLS443 + Rust M4，五独立租约、单服务端、六个 netns。复用已冻结三件 ELF183 的 SHA/manifest，不修改产品协议、加密、FEC 或真实业务。36 文件原归档 artifact 13602256980，ZIP SHA256 `84f00d0586b19b7e32048fc195efb67e703d52ca8304d4d8e599b4ba1db75695`，全部 CRC PASS。
- 五个用户严格**只在指定一个方向**发 UDP，反方向真用户 UDP/TCP 和测试探针为零，但原 TLS/Health 控制保留。实际物理损伤按客户端0/1/5/15/30%和0/15/50/100/125ms配置，真实 Erin kernel qdisc 上行丢包 29782/(70351+29782)=29.742%，下行2369/(5639+2369)=29.583%，10份物理 veth ARP 均按真实 MAC 正确安装。
- Alice 上行 38124800/38124800B，Bob 下行38122496/38124800B，Carol 上行30418944/30500864B，Dave下行30482432/30500864B，Erin上行29867520/30500864B。最大10ms活跃发送无收窗口分别为0/10/50/100/120ms；所有五客户端最终 Stop 和服务端共享TUN Stop、server lease queue overflow0，应用错误0，发生器容量限制0。
- 4vCPU 宿主总忙碌四阶段均值11.01/15.36/17.62/14.94%，最忙单核阶段均值11.78/15.74/17.73/15.50%。本场是容量内180秒单向弱网稳定性，非产品单独CPU比较。
- **下一项**：保留上述完全相同弱网和原始加密链路，激活恰好两轮真实 owner renewal，检查 Normal Off 纯上行与 Fixed6 纯上行是否取得服务端 M4/Health 接管证据及每10ms业务中断。历史 H1317 SOURCEe61b 原始 FAIL（Normal Off 96.14s、Fixed6 91.83s）及 H1319 SOURCE4c12 scoped positive 均不改写。Windows 双独立真实设备、MTU多模式生命周期和最终L3仍需覆盖。

```feature-impact
{"kind":"updated","ids":["arm64-targets"],"reason":"Index H1361 source24e true native ARM64 five-client original pure one-way 30pct125ms physical-impairment short test with original ZIP verified; distinguish dormant timers from future actual owner renewal and preserve H1317 old-source failure."}
```
