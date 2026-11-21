# M0 PLAN029 H2293 · 双组完整 Windows→ARM 原产品 FEC2 弱网因果对照（WIP）

## 真实任务，不再重复夹具容量赛
- 权威 main cursor H2292 已 [Action44951274107](https://github.com/lly8666/wbd-next/actions/runs/44951274107) SOURCE `13d391cbb64ef06c55b046c6d73a2d69e096c54d` **9/9 PASS**：两组各Win2025原签名 Npcap/Wintun + 原Go TLS/Rust owner → 独立ARM Linux内核双向netem relay → 独立ARM原GoTLS/Rust AF_PACKET/TUN，真实4×25s业务TCP＋160稀疏TCP、原WAL/ARM Stop。每组同机A旧TX8/NPF16KiB→B TX16/NPF64KiB→A′旧，A129.189/189.617/125.835Mbps、原Win CPU秒/实收GiB44.529/28.150/45.997、P99266/188/250ms；B119.277/139.332/110.180Mbps、CPU48.754/39.436/52.198、P99297/313/375ms。TX16候选改善了跨机无附加损伤的两个组的goodput与CPU/GiB，但还不能默认ON，弱网未验。
- H2284确认八流高供给/大Windows SO window使裸TCP直连1Gbps、B组relay近1Gbps；以往8Mbps是夹具容量/窗口问题；H2292已经接上**完整原Windows/ARM产品**，绝不复测只用Winsock Python的低价值工况。原 Go TLS/Rust真实SOURCE的Windows两份Rust DLL由之前已真实编译的 `dc2da4b98ecc419a67e3e2ee6530f944b78d88ef` 出品，基础features完全相同，候选仅 `h2291_windows_tx_service`，原Go EXE source c5066db，ARM原bundle 97db898。H2292工作流真实git diff确认截至最新SOURCE产品代码无变化（只夹具），复用实际DLL与ARM bundle，避免耗时重复构建。
- 本次专注**1% 与5% 真双向200ms损伤分别是独立Actions**（避免把不同波形/不同VM/不同snapshot混成同一数据）；每Action内2个完整独立3runner组，同SOURCE、同时起两组、每组同一Win/ARM VMs顺序 **A off→B fixed→A′ off**。每腿保持同一 `TX16/NPF16×64KiB` 编译DLL、同Go EXE/ARM二进制/route-key授权、同真实Wintun/TUN业务、4×25s负载和160 echo，**唯一比较因素是FEC2原生cold Fixed**。1% B选 light(0)，5% B选 mild(1)，A/A′均原Normal/off，原外层机会原密文修复固定关闭，Go仍只负责TLS/OS冷控制，Rust真正稳态。
- Windows original V4 mode selection要求 `--fec-mode fixed --fec-parity 4` **仅作旧V3承载兼容**，以及 `--fec.mode fixed --fec.profile light|mild` 作为 FEC2 k≤16原生分配。OFF为 `--fec-mode off --fec-parity 0 --fec.mode off`。不把旧V3 parity4冒充FEC2实际repair。原 Rust feature7协商后必须由 **`WBD_WINDOWS_FEC2_INSTALLED mode=fec-fixed profile=0|1 revision>0 applied=1`**真实原产品日志读回；A/A′不得冒出该状态，B不得只信命令行文字。
- 由原relay唯一认证UDP4789控制面将 `A_off,B_fixed,A_prime_off` 明确为同组内严格递增阶段（继续复用原H2292同来源ready协议，ARM server真Ready后Windows才启动原 GoTLS/Rust）。Windows每腿在**冷Go FakeTCP/TLS握手之前**调用已验证的relay双向真实netem `delay 200ms loss 1|5%`，原TLS/签名驱动/原WAL任务要真实成功，然后在开始内层TCP前刷新netem readback以排除先前阶段累计计数；经过25s真实业务两个方向 `tc -s -j qdisc`必须都有发包和非零真drop。未回或受限如实保留而不伪造成成功；H2292无损Go握手不替代本次真弱网握手。
- 每段实际收到的ARM TUN内层TCP应用字节、有效 goodput、160小TCP P99/迟回、原Win32原Go/Rust进程CPU秒/有效GiB和Rust TX线程下界、relay tailscaled实际CPU秒/最忙核、实际内核netem egress/drop、Win WSL kernel NAT、FEC2 Applied、原ARM TUN UDP、精确source/DLL SHA、原Win WAL/驱动Stop及ARM netns/sysctl Stop逐段保存。同VM比较B相对A/A′吞吐/CPU/GiB和P99；**不用要求B一定更快以制造PASS**，观测合格≠性能胜出，2组均汇报、不能只择优。
- 原H2274 ARM单机Normal FEC2 off→light/mild→off在1/5%改善真实ARM原Go/Rust goodput及P99，但这不是原Win跨机证明；若H2293 1%/5%候选未明显改善或P99恶化，首先分阶段定位真实 FEC2 block形成/repair、inner TCP retrans、RX首次交付与丢包分布，不盲目扩M1/M4软件队列；若当前Netem网络容量不足/DERP或签名WSL先行报INFRA失败而非WBD。
- 源码范围仅 `tools/m0_h2293_true_product_fec_loss.py`（沿用H2292原程序判定和同源编译缓存）、原 `tools/m0_h2286_full_windows_product.py` TEST-ONLY opt-in Cold FEC flags及loss计数、 `tools/m0_h2276_three_runner_tcp.py` 原认证relay stage tag、两份 loss1/loss5 CI workflow及限域unit。**没有更改产品Go/Rust/Cargo源码或Win签名驱动默认**，H2292旧试验和既有正常产品继续OFF。本workstream仍在Draft PR#68，整包done_when包括后续Linux/Win受影响配置、P99、Stop、CPU及丢包资格。

## 结果状态
H2293两份workflow初始实现推WIP后，先核同源静态 Actions；原生两组分别带 `[m0-029-h2293-fec2-loss1]` 和 `[m0-029-h2293-fec2-loss5]` 提交marker才执行昂贵测试。**本记录创建时两个真实弱网结果均 NOT_RUN**，不将夹具实现写成产品已改善。

```feature-impact
{"kind":"none","ids":[],"reason":"H2293 only source-locked existing signed Windows+ARM original product weak-loss Normal FEC2 OFF/Fixed/OFF test harness, per-loss two identical independent triplets and real kernel/readback/Stop verification; no product GoTLS/Rust default, driver, mode or config changed."}
```
