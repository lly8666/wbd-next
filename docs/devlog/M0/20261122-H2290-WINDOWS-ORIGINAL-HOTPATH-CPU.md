# H2290：完整 Windows 原 GoTLS/Rust 热路径 CPU 分段 + 双组三Runner结果构件收尾

日期：2026-11-22。角色：M0 PLAN029。实验分支：\`experiment/m0-029-throughput-arm-fair\`，PR#68 Draft。

## 先保留真正完整 Windows 客户端基线，不再拿 Winsock 冒充

H2289 精确夹具 SOURCE \`7c431364afaeb42a7cf5e138a3fb1a92a30169ec\`，原Win GoTLS/Rust编译SOURCE \`c5066db61fc51bafd7c2ad2def3029e615efa777\`（源diff0＋原构件SHA锁定），ARM原GoTLS/Rust原生编译SOURCE \`97db898f3a1fbebcdeea7f2a1b9d9c3dfcd32573\`（同原编译产品输入git diff0＋构件SHA锁定）。[H2289 Action44939085405](https://github.com/lly8666/wbd-next/actions/runs/44939085405) 的**两台独立Win2025原签名Npcap1.88＋Wintun0.14.1+GoTLS/Rust客户端**各自Job真实SUCCESS，原客户端\`client-result.json\`原始ZIP A\`14720907066\` B\`14720459283\`已核实，Go TLS真实authenticated与OS Applied、Rust M4、双向原内层UDP、ARM真实Rust TUN内层4TCP、160个稀疏回显、Linux内核中继双向真实TC发包、Windows原Rust/WAL Owned Stop全部有原始回执。旧H2288真实ARM TUN tcpdump显示五条错发18727 SYN遇RST；H2289只修测试脚本把**内层真实TCP端口45902与外层relay18727分离**，原Go/Rust源码、驱动/默认均没改。

具体已实际测到的原产品持续4TCP 25s (测试only2MiB Socket):
- A：ARM原Rust TUN真TCP应用接收 **378,322,944B / 25.515s，118.620Mbps**，稀疏160/160，P50 172ms、P95 265ms、P99 **281ms**、迟回>1s=0；Windows整机（**包含 Tailscale/WSL2/driver**）忙碌 **88.211%**；原WAL/Rust Stop PASS。
- B：ARM真Rust TUN接收 **492,257,280B /25.421s，154.914Mbps**，稀疏160/160，P50 203ms、P95 250ms、P99 **297ms**、迟回>1s=0；Win整机忙碌 **85.758%**；原WAL/Rust Stop PASS。
- 相比H2285两组Windows Winsock+WSL内核路由到ARM的纯OS数据A468.211/B496.194Mbps，原产品同类流的结果约为25%/31%参考（**注意ARM原Rust AF_PACKET/TUN与H2285内核TCP路径、额外TLS、Npcap/Wintun/crypto/MTU不同**，不能直接把绝对差额归因一个函数），真实产品CPU/GiB和WSL/relay/ARM分段缺失。H2284干净relay A680没达800Mbps底层容量门，B995通过；不能跨VM挑最好group推默认。

## 发现客户端结果双组PASS但ARM/relay后置任务空等的夹具缺陷

H2289原Windows发布名\`h2276-a/b-client-result\`的构件**同时包含**\`h2276-out/client-peer.json\`和\`h2286-out/client-result.json\`（多个顶层目录）。原H2276跨job下载等的是只有一个顶层\`client-result.json\`，\`await_artifact\`只从当前构件根查找JSON，两个顶层目录造成**两台Windows已PASS，ARM server/relay仍在无意义的构件轮询**。不是端点新的业务失败，不能让它长时间占Runner。

H2290精确修复：在Windows原Go/Rust Owned Stop及kernel NAT资源清理后，额外将完整\`client-result.json\`以TEST-ONLY形式存到\`h2276-out/client-result.json\`，跨机同步的旧名 artifact改为**仅\`path: h2276-out/\`单根目录**，其中同group+run+SHA仍强制验证产品status、实际TCP/UDP/P99/Stop及所有relay计数；所有原Windows日志、真实CPU原始样本、完整原结果放第二个\`h2290-{a,b}-original-windows-hotpath-raw-evidence\`单独审计构件，两个构件职责不混合。旧H2289原始Windows PASS证据留存不重写。

## 真 CPU 热路径归因：只读真Windows原 Go/Rust进程＋relay tailscaled

复用项目已存在的\`tools/m0_wl_native_resource_sampler.py\`原Win32\`GetProcessTimes\`、\`GetThreadTimes\`、Toolhelp快照线程名\`wbd-native-tx/rx\`，不是创造新产品线程，也不转发任何数据，真正原GoTLS/Rust Windows进程从启动前一直每1Hz记录PID、Win32原进程CPU用户/内核秒、RSS、top6线程原生内核/用户CPU。新的纯计算\`tools/m0_h2290_windows_hotpath_cpu.py\`**只取真实Wintun/TUN bulk25秒相同monotonic采样窗口**，要求至少14个且同一真实PID、累积CPU计数单调，算原Go+Rust一起的总CPU秒、内核CPU、用户CPU与ARM实际业务GiB分母CPU s/GiB、Rust原TX/RX工作线程及未命名线程保留UNKNOWN的top6下界，不能把未知CPU叫Go/AEAD/NPF阶段，也不能把Win32原进程kernel time当DPC/ISR或Npcap Driver全占。

同时在真正bulk前后的ARM Linux relay调用已有**真实/proc/stat Host allcore/最热core+tailscaled PID utime/stime**阶段差分\`core.relay_resource_delta\`；要求同一tailscaled PID存在，否则因真实双跳CPU证据不全不计资格。最终每组一起写\`windows_original_go_rust_cpu_stage\`、\`relay_tailscaled_and_host_cpu_stage\`、Win Host全核忙碌、ARM真实收端字节/P99、Windows Rust原Stop，确保先分清瓶颈是Win原Go/Rust还是tailscaled/relay/驱动/系统。**不改任何生产Go/Rust参数/default/Stop/FEC2**。两套源锁相同条件必须全部完成；新的CPU采样失败也必须留原业务失败与原始日志，不能伪称本轮CPU PASS。

## 下一步性能修复的具体改判

- 若真Win原Go+Rust CPU接近或超过一个逻辑核，且rust native tx/wake或系统调用CPU占大头，对准\`crates/wbd-engine/src/v4_windows_native_runtime.rs\`已存在的原实际\`WBD_WINDOWS_RUST_NATIVE_WAKE_BATCH\`与TX调用/32 cap、batch/借用热路径做**一个可归因小改动**，新Win源构建而不是复用旧c5066，A→候选B→A′同一VM或同类并行组记录真实Win/ARM产品goodput/P99及Stop，出现尾时延、丢包或CPU/GiB退化则否决。不允许靠加大SharedTun队列交换高P99。
- 若Win原进程CPU不满而Win host busy仍88%，优先核Windows tailscaled/WSL/系统内核和真实Npcap驱动路径，避免改Rust。
- 若relay tailscaled最热核先饱和、A/B网络有漂移，优先复用旧H2228独立双VXLAN/noNAT作为真实原Windows二层出口容量门（仍须真Npcap），不要将夹具限速算产品失败。
- 原版Normal/off真实0%仅是初始带外测量，不等于 PLAN029完整收敛；后续独立0/1/5%每向200ms/原FEC2 off/fixed/off、双向业务及正确Stop仍OPEN。PR#68继续Draft。
