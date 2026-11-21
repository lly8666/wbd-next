# M0 PLAN029 H2291→H2292 · 完整Windows原客户端发送热路径真实结果与同组三腿对照（2026-11-22）

**原任务 M0-PLAN029-THROUGHPUT 仍 OPEN。** 正式业务必须是两套各三台独立 Windows2025 签名Npcap/Wintun+原GoTLS/Rust 客户端→ARM64 Linux内核relay→另一ARM64原GoTLS/Rust AF_PACKET/TUN，真TCP接收/160小TCP P99/Win三机CPU/本机drop/原Stop。不以裸OS kernel TCP替代，不以跨VM最高组数据声称产品优化获益。唯一研发分支 `experiment/m0-029-throughput-arm-fair` Draft PR#68，main仅恢复控制面。

## 已完成的原全产品H2291
精确 SOURCE `f9329239733aa40698378a2882d0eb4621e9ebc7`、[Action44941989692](https://github.com/lly8666/wbd-next/actions/runs/44941989692) **9/9 SUCCESS**。Windows真实MSVC NPF sendqueue 7/7原生单测（16个ready frames feature-on仅一次queue传输，off两次并测真实partial），单次Rust release DLL PE导出/SHA256 artifact14722156403，ARM原GoTLS/Rust真实二进制已源锁复用，两套真实签名Windows原Wintun/TLS/Npcap→ARM原Rust TUN TCP都有真实`H2291_ORIGINAL_WINDOWS_RUST_NPF_TX_SERVICE_PROFILE nqueue=1 queue_bytes=65536 max_frames=16 ready_only=1`，各自原Rust/WAL/系统清理Stop成功，原NPF本机 ingress local drops=0。
- A：ARM TUN真正收到561463296B/25.406秒，**176.797Mbps**，160/160 echo，P50 250ms **P99 312ms**；Win整体busy86.105%，原Go/Rust进程16.96875CPU秒=**32.451CPU秒/实际ARM GiB**，原Rust TX OS线程CPU下界13.1406s、RX3.4219s，relay tailscaled约1.593核、最忙核49.621%；原日志/CPU ZIP14721998486、单根客户端receipt14721893863。
- B：ARM收到378044416B/25.906秒，**116.743Mbps**，160/160echo，P50 266ms **P99 344ms**；Windows整体88.263%，原Go/Rust进程17.57812CPU秒=**49.9263CPU秒/实际ARM GiB**，TX13.000s、RX4.2344s，relay tailscaled约1.589核、最忙核51.503%；原ZIP14722176818、单根receipt14722161634。
- H2290不同VM源d5690ef…原8ready版本 A154.675Mbps/P99250ms、B80.902Mbps/P99125ms，**不能用这两次不同Runner的数字算TX16候选收益**。并且旧c506 DLL与H2291 DLL在Cargo基础feature集上并不完全一样，混合比较会犯因果混杂。现在证据只支持候选全产品可运行，且P99并不理想；不能晋级默认/判定优于原版。

## H2292有辨别力的接续施工
研发 SOURCE `c3c0745be16db6baf9d28923fbea3af532ff3e2f` [H2292 Action44943590620](https://github.com/lly8666/wbd-next/actions/runs/44943590620)。本控制面记录时静态真源码单测SUCCESS，ARM真实旧GoTLS/Rust二进制源锁复用SUCCESS，一台Windows builder正在从**同一SOURCE/同一Rust基础特性**各编译默认8ready/16KiB和显式候选16ready/64KiB两版原生DLL，以只差`h2291_windows_tx_service`特性解决编译混杂。其后每组只有三台独立真实VM，原签名Windows客户端在**同一台Win宿主**按 A原DLL→B候选DLL→A′原DLL顺序各重新原GoTLS认证、原Npcap/Wintun→ARM原Rust TUN真4TCP×25s、160echo、源级CPU秒/GiB、P99、每阶段真Rust/WAL Stop，ARM原服务端同一宿主三次独立真实内核TCP监听+UDP、并由本组ARM通过现有relay4789认证控制通道发阶段ready。**未产生全组三腿业务结果**，9job Action未完成，不可先报性能胜利。实验源码默认off，原Go TLS/ARM binary/driver app config未修改。
- 此处已发现H2291提交的feature-catalog声明缺少`ids:[]`导致原相关governance Action失败；研发docs-only `c602997d4d3548ebd9c7eb81eb7addf2bc02d73e`修复为schema合法`kind:none ids:[]`，不另触发昂贵H2292分支runner、不动default。
- 下一必须从实际Action和两个组原日志、真实本机CPU/ARM接收/3次Stop收全数据，按组内B相对(A+A′)/2和小TCP P99/CPU/GiB联合判定，不能挑有利一组或拿裸OS流当产品。只有双组真实改善且尾延迟不恶化才考虑继续；否则否决TX16测试并回头找Windows NPF/Wintun内核调用、WSL2或ARM RX热点。后续双向200ms 1%/5% FEC2 OFF→ON→OFF仍OPEN，原完整任务done_when未达。
