# H2282 · 双套Win→ARM三Runner 真400ms TCP窗口A/B/A′（测试夹具，非产品代码）

## 已收证据与瓶颈理由（精确SOURCE）
[H2281 Action44929074737](https://github.com/lly8666/wbd-next/actions/runs/44929074737) SOURCE `e49b1ecf651063ae1a2e8c141a14ed7ea6f83dc3`、attempt1 **七jobs全部SUCCESS**。两套互不共享VM的Windows2025 Winsock client＋ARM64 Linux中继＋另一ARM64 Linux服务端，真内核TCP四bulk持续 >25s、160 sparse TCP和双方netem packet/drop kernel readback全PASS。

- A组无附加时延67.794Mbps、双向200ms0% **8.485Mbps**、1%3.361Mbps、5%1.113Mbps；P99分别63/469/1156/1703ms，5%晚于1秒39/160；CPU Windows各档10.697/1.944/1.581/1.963%（allcore），ARM5.718/1.076/.755/.646%。0%实际Win发送经ARM收到27.38MB，bulk墙钟25.813s。
- B组无附加时延60.644Mbps、双向200ms0% **8.409Mbps**、1%3.449Mbps、5%.970Mbps；P99分别78/469/469/1781ms，5%晚于1秒29/160；CPU Windows各档19.567/2.469/2.179/1.557%，ARM6.719/1.227/.877/.638%，0%已收26.87MB/25.563s。每档双方向有独立qdisc发包，1/5%双向真实drop非零，Tailscale双方直连候选。两组三机高延迟无损**近似稳定在8.4Mbps**、原始TCP上限远没被CPU消耗，不是H2279短流供给不足，但 relay tailscaled CPU热点与真实TCP snd_wnd/rcv_wnd仍未测齐。
- 这是**Win/ARM操作系统TCP网络/夹具结果**，不是WBD原GoTLS/Rust/Wintun/NPF业务。原产品在1%5%弱网表现差不能自动归因为此底层，但更不应盲调产品M1软件队列。

## 本次有区别的唯一候选
为挑战“当前原Winsock发送/ARM接收默认Socket Buffer导致400ms长RTT约8.4Mbps”的假设，在**同一个实际Win/ARM client-server、同一ARM relay、同一个真实内核TC 200ms每向0%损伤/同一25s四TCP＋160echo负载**下顺序重复 **A默认→B 8MiB SO_SNDBUF/SO_RCVBUF→A′默认**。两组三台原生各自同序测试，全程保护同一SOURCE、真实Tailscale直连/端口18727、两个netem实际通过pkt差分，不仅是工具描述。
- B在四条实际Windows Winsock bulk sock的connect之前设置8MiB SO_SNDBUF/RCVBUF，输出4条实际OS readback（可能裁剪则如实记录）；原ARM listener在listen之前设置同档8MiB并在SERVER_DONE保留listener及接受连接的真实OS readback。A/A′不调用setsockopt，只readback；被保护的160小TCP echo无需人为大buffer，不因候选改变业务优先级。
- 为让真实ARM Linux SO_RCVBUF有足够内核上限，单测试VM在全三段期间相同应用级sysctl `net.core.rmem_max/wmem_max=16777216`，测试前读取旧值，Owned Stop的 `finally`恢复旧值并有恢复标记，确保A/B/A′同一OS上限。不得把host测试sysctl当原WBD生产默认优化。
- B仅针对窗口这一因素，明确记录goodput A/B/A′、Win/ARM allcore CPU、每段160小TCP P99/late以及原系统Socket buffer实际读回；任一腿bulk不足15s、ARM真字节不齐、双方qdisc缺流、套接字读回缺失或owned restore缺失都FAIL。**不要求B一定高于A/A′，失败/负结果保留**，避免对环境波动只挑有利单组。A/B之间不跑1%/5%，这是有界的零损高RTT窗口容量判别，后续才把有效配置带进1%/5% FEC2候选，仍必须两组各三台。
- `WBD_H2282_TCP_WINDOW_AB=1` 只在 `qa-h2282-dual-arm-relay-window-ab-tcp.yml` 的原Win/ARM三机验证中启用；原签名Windows+WSL2测试用 `tools/m0_wl_loss_tcp_probe.py` 原默认 `WINDOW_TEST_BYTES=0`，保持24MiB/18s与原端口45902；其余所有Go/Rust/Wintun/NPF代码、默认、安全/Stop完全不改。新六机昂贵执行只在精确提交marker `[m0-029-h2282-window-ab-3runner]` 执行，纯数据/修复push只跑静态不重复大矩阵。

## 下一决定
若8MiB B能在双组显著提高真实接收goodput、P99仍合理、CPU余量足，继续找较低缓冲/内核窗口上限的最小可用值（别引入排队）；否则撤回该试验性socket请求，改查Windows原生TCP sender cwnd/Win TCP autotune、ARM rcv_space、tailscaled relay单核CPU/softirq与SACK/RTO。真正产品再按此前原ARM H2274 FEC2 light/mild弱网相对OFF显著增益，部署到同一双组三runner原Windows Wintun/NPF＋ARM Rust，绝不把OS Winsock前置当WBD吞吐获胜。

```feature-impact
{"kind":"none","reason":"H2282 only native dual-three-runner test socket buffer AB/A-prime and owned ARM sysctl restore/readback, original WBD client/server/Go Rust/Windows driver/default untouched."}
```

## 第一轮精确SOURCE静态失败与回归修复
- [H2282 Action44929841876](https://github.com/lly8666/wbd-next/actions/runs/44929841876) SOURCE `90119c7667effe4d97779e9758f09b2d61463081` 的 static 检查 FAIL 于旧 H2279 测试 `test_h2279_clean_path_uses_identical_windows_and_arm_real_tcp`：在H2282全局env启动时，`active_stages()` 按设计返回 `('base','tuned','base_prime')`，旧测试却无隔离地期待 H2279 `('direct',-1)`。共23项仅此1项失败；六原生Runner严格由needs:static跳过，**没有产品/网络/性能样本**。
- 修复仅在旧H2279测试内临时 `patch.object(h,"WINDOW_AB",False)`，保持H2282自己既有真实socket setsockopt/getopt回归和全部真实产品验证门；不修改H2279或H2282生产模式路由，也不依赖跳过单测。后续再按两组三Runner源锁校验，不将本static FAIL描述为TCP窗口负结果。

## H2282 静态模式隔离与中央完整治理回归
- 第一_SOURCE `90119c7667effe4d97779e9758f09b2d61463081` [44929841876](https://github.com/lly8666/wbd-next/actions/runs/44929841876) 因旧H2279 mode测试未隔离H2282 global flag而static FAIL，六机从未启动。第二_SOURCE `cb09a27013e391b338a782b21ead9b82a8f3d675` 仅修旧H2279局部单测，H2282 真实 [Action44930023496](https://github.com/lly8666/wbd-next/actions/runs/44930023496) static SUCCESS并已启动两套六VM；保留本轮真实结果独立核收。
- 中央 governance-maintenance 在缺省 env 环境下执行所有必跑unit，自带H2281/H2282 mode-specific测试原先错误要求CI运行时必须带 `WBD_H2281_SUSTAINED_TCP=1` 和 `WBD_H2282_TCP_WINDOW_AB=1`，导致另一条维护检查在源码正确时FAIL。此次改为每个测试自己启一个短暂独立Python解释器并以真实opt-in env import源模块、读回 `SUSTAINED/WINDOW_AB`及bulk供给配置；小Winsock/Linux socket setsockopt readback测试用精确 `patch.object(WINDOW_AB,True)` 隔离。这样同一测试在维护的空env和真实三Runner的opt-in环境都要通过；不降低模式/CPU/业务资格门，不改变Go/Rust/Wintun产品。
