# M0 PLAN029 · H2289 原完整 Windows 双组三机吞吐与 H2290 CPU归因恢复（2026-11-22）

进度 partial，PR #68 Draft，项目 GoTLS/Rust 生产源码、签名驱动、默认和 Stop 均未修改。

## 旧3runner经验转成正确容量门

老H2228 Linux x86→ARM中继→Linux x86双VXLAN无NAT、BBR/64MiB/8流，0ms原生TCP上行848.551/下行861.757Mbps，但原WBD完整矩阵失败。新H2284的两组Win2025→ARM relay→ARM真实内核原生8TCP大窗口25秒干净直连1286/1068Mbps、干净ARM中继680/995Mbps，A组没有通过800Mbps双跳容量门，B组通过。H2285先证明Windows→本机真实WSL2 Linux kernel NAT→独立ARM relay→独立ARM OS TCP在4TCP25s为A468.211/B496.194Mbps、各160小TCP回显，此为裸TCP基线，不是产品性能。

## H2289 首次真正完整 Windows 原产品双组三机收到TCP应用字节

精确实验SOURCE 7c431364afaeb42a7cf5e138a3fb1a92a30169ec，真实Action https://github.com/lly8666/wbd-next/actions/runs/44939085405 。真实Windows2025签名Npcap1.88+Wintun0.14.1，原Go TLS/Rust完整Windows客户端→真实WSL2原生内核转发→独立ARM Linux relay→另一独立ARM64原GoTLS/Rust真实wan0 AF_PACKET与TUN服务端。Windows原编译产品源码c5066db61fc51bafd7c2ad2def3029e615efa777、ARM原编译产品源码97db898f3a1fbebcdeea7f2a1b9d9c3dfcd32573，逐次源码零变更和SHA锁定复用构件。原Win GoTLS authenticated+OS Applied、原Rust真实内层双向UDP、真正Windows Wintun↔ARM原Rust TUN内层TCP、两个方向真实relay内核qdisc和原Rust/WAL Owned Stop，都由真实原始结果验证：

- A组Windows产品Job SUCCESS，ARM原业务TCP收378,322,944字节/25.515秒=118.620Mbps，160/160小TCP回显、P99 281ms、超过1秒迟回0，Windows whole-host全核busy88.211%，真实Stop PASS。
- B组Windows产品Job SUCCESS，ARM原业务TCP收492,257,280字节/25.421秒=154.914Mbps，160/160回显、P99 297ms、迟回0，Windows whole-host busy85.758%，真实Stop PASS。
- 旧夹具在H2288前原Windows内层TCP被共用全局tcp.PORT误改为外层18727，而ARM真实监听45902；真正ARM TUN抓包看到Windows SYN→18727与内核RST。这属于测试端口串用，H2289只在原Win Wintun/TUN内层测试显式用45902并保留外层relay18727、退出恢复，未改WBD产品源码。当前所有原业务数字都是后修复的新实际收端字节，绝非 Winsock 代替。
- H2289两台Windows Job完成SUCCESS，后置两台ARM server与ARM relay还卡在跨作业artifact目录结构检查：原命名h2276-a/b-client-result的ZIP同时包含h2276-out与h2286-out两个顶层目录，旧等待器只查artifact根目录client-result.json。业务已成功但后置Stop/Runner等待是夹具归档布局缺陷，不能当作产品失败或整条Action SUCCESS。

## H2290 立即改进效率并补真CPU热点定位

研发SOURCE d5690ef41ca5fb40313375b82e1761dd6f95a4d1，完整双组三Runner原客户端再次执行 https://github.com/lly8666/wbd-next/actions/runs/44940140123 。Windows原客户端成功结束后把最小已签名同run/source/group结果发布成仅一个h2276-out根目录的旧名构件，详细原Windows Go/Rust日志与Win32 CPU样本独立审计artifact。ARM server和中继按原真实业务/P99/Stop收齐后可以及时结束，不再因Zip两个根而长时间等待。

基于已存在的tools/m0_wl_native_resource_sampler.py只读Win32 GetProcessTimes+Toolhelp GetThreadTimes每1s采样原Go+Rust**同一进程**，新tools/m0_h2290_windows_hotpath_cpu.py只按真正Wintun→ARM Rust TUN持续25s窗口累加原Windows进程user/kernel CPU、CPU秒/ARM真实GiB、原Rust TX/RX实名线程CPU下界与UNKNOWN其他线程；并在同窗口读ARM relay真实tailscaled PID CPU秒与整机最热核和allcore忙碌。严格禁止把Windows whole-host busy86-88%直接说成原Rust CPU已经饱和；Go/Rust共用进程、Npcap Driver/DPC/ISR和tailscaled不归原进程的部分需分开。不增加产品线程，也不改热路径默认。

下一动作：两组H2290真正CPU+真实TCP/P99/Stop读回后按首个饱和点实行小范围可回退产品热路径单因素优化，重新构建受影响原Windows源码做原A→候选B→A′，以吞吐/两端CPU秒每GiB/延迟P99和原Owned Stop共同判定，不以更大队列牺牲小流。双向各200ms及真实损1%/5% FEC2 OFF/fixed/OFF、实体平台仍OPEN，PR#68继续Draft。
