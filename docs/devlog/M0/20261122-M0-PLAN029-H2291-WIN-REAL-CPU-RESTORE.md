# M0 PLAN029 H2290→H2291 · 原完整Windows→ARM吞吐瓶颈与施工恢复（2026-11-22）

**任务仍为 M0-PLAN029-THROUGHPUT，原完整 Windows2025 Npcap/Wintun + Go TLS/Rust 客户端、独立 ARM64 relay、独立 ARM64 原 GoTLS/Rust TUN 服务端，双套三 Runner。** 最新实际进展优先看实验分支 `experiment/m0-029-throughput-arm-fair` Draft PR#68；以下不是产品优化结果晋级。

## H2290 已收真实 8/8 全通过，必须与H2289不同SOURCE分开
[Action 44940140123](https://github.com/lly8666/wbd-next/actions/runs/44940140123)，精确源码 `d5690ef41ca5fb40313375b82e1761dd6f95a4d1`，8/8成功。两组真正原Windows Npcap1.88/Wintun0.14.1、Go TLS/Rust客户端到独立ARM原Rust TUN的25s连续四TCP、160次小TCP；原Owned Stop、签名驱动清理和两端真实收字节均通过，修复了H2289两根artifact造成ARM后置假等待。
- A：ARM真实收到491,520,000B，**154.675Mbps**、P99 **250ms**、160/160无>1s迟回。Windows主机全核busy83.673%，但同窗口原Go/Rust进程**17.703 CPU秒/25.031s=0.707核**，kernel时间14.578s占82.35%，每ARM有效GiB38.673 CPU秒；原Rust TX热OS线程下界12.234s（kernel10.281），RX5.094s（kernel4.047）。relay tailscaled在25.509s消耗39.890 CPU秒=1.564核、relay最忙核48.96%。
- B：ARM真实收到262,619,136B，**80.902Mbps**、P99 **125ms**、160/160无>1s迟回；Win主机busy62.049%，原Go/Rust进程11.328 CPU秒/24.422s=0.464核，kernel9.313s占82.21%，每GiB46.316 CPU秒；Rust TX7.922s（kernel6.594），RX3.109s（kernel2.469），relay tailscaled27.650CPU秒/26.145s=1.058核、最忙核36.92%。真实客户端A/B原raw 14721287235/14721376734、ARM 14721491245/14720254736。原始详细结构化证据：实验分支 `docs/evidence/M0/PLAN029-H2290-WIN-ARM-REAL-TX-RX-CPU-20261122.json`。
- **归因边界**：真实原Windows进程和Rust TX/RX并没有到单核满载，不能把Windows整机60%–84%忙碌直接归给Rust；内核时间虽占主导，但函数级阻塞点与驱动DPC/ISR、WSL2和tailscaled成本仍待区分。不同VM的A/B组差异不用于声称因果提速。此前裸TCP H2284直连>1Gbps、H2285 Windows→WSL2→ARM 468/496Mbps，只是环境参考，不是原产品成绩。

## H2291 已授权小范围实际Windows热路径施工
- SOURCE `f9329239733aa40698378a2882d0eb4621e9ebc7`，新 [H2291双组三Runner Action44941989692](https://github.com/lly8666/wbd-next/actions/runs/44941989692)。该工作流的静态Python套件已成功，ARM原构件复用验证已成功，唯一Windows Rust候选DLL编译/本机测试正在进行，**完整候选业务还不能写PASS**。
- Windows原Rust TX入Wintun的现值每次8 ready M1记录×4批，每轮最多32 ready；原Npcap队列仅8帧/16KiB，TX OS线程kernel时间高，存在优化一次系统调用/owner lock固定成本的合理可证伪动机。候选**编译特性默认OFF** `h2291_windows_tx_service` 只让每次16 ready×2批（仍总32、不等凑批）、Npcap队列16帧/64KiB，保持小TCP Direct回程每轮8个、公钥认证/原M1原密文/真实驱动prefix/Stop不变。新的Windows builder只构建一次同SOURCE候选Rust DLL，复用原Go EXE实际hash与ARM原二进制；Windows签名驱动和原GoTLS/Rust真实路径必须执行两套组；若不是真实Npcap queue=1/65536/16自动FAIL。无任何默认/全模式配置变化。
- 未来验收：候选本轮两组要先验证实际Windows原产品真吞吐/P99/CPU/Stop并记录为**非配对诊断**；将同一Win/relay/ARM依次原DLL A→候选DLL B→原DLL A′做配对（包括真实8/16 sendqueue及OS字节收回）后才能判断受益/否决，既不能挑快组，也不能拿H2290跨Runner与H2291新Runner的差当收益。若无改善，检查Npcap sendqueue实际每批包数、Wintun wake、WSL2 DPC和远ARM RX。下一阶段真实1%/5%双向损伤与FEC2 on/off、上传/下载、公平/P99仍OPEN，包整体未达到done_when。

main S只记录真实事实，随后仅游标 H 指向 S；产品分支 PR#68 保持Draft。