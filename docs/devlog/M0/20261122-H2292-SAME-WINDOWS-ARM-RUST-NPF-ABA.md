# M0 PLAN029 H2292 · 两套同机组三次完整 Windows→ARM GoTLS/Rust 真实产品 A→B→A′

## 问题与已有事实
- H2290 SOURCE`d5690ef41ca5fb40313375b82e1761dd6f95a4d1` [Action44940140123](https://github.com/lly8666/wbd-next/actions/runs/44940140123) **8/8 SUCCESS**，原Win2025签名Npcap/Wintun GoTLS/Rust→独立ARM kernel relay→另一独立ARM原 GoTLS/Rust AF_PACKET/TUN，25秒4TCP真实A154.675Mbps/P99250ms、B80.902Mbps/P99125ms、原Win进程CPU17.703/11.328s、TX线程下界12.234/7.922s，大部分进程时间为内核态。该运行是在不同VM上，不是H2291候选的同一物理条件。
- H2291 SOURCE`f9329239733aa40698378a2882d0eb4621e9ebc7` [Action44941989692](https://github.com/lly8666/wbd-next/actions/runs/44941989692) **9/9 SUCCESS**，实际Win32 NPF编译单测7/7、Windows Rust DLL PE/SHA artifact`14722156403`、两套原签名Windows完整GoTLS/Rust双组三机成功；A ARM真TUN接收561463296B/25.406s=**176.797Mbps**、P99312ms，160/160，Windows进程16.96875CPU秒/32.451s每有效GiB、TX线程13.1406s，relay tailscaled1.593核，原Stop通过；B ARM收378044416B/25.906s=**116.743Mbps** P99344ms、160/160，进程17.57812CPU秒/49.9263s/GiB、TX13s，relay1.589核，Stop通过。两个真正原Win客户端日志均读到`H2291_ORIGINAL_WINDOWS_RUST_NPF_TX_SERVICE_PROFILE nqueue=1 queue_bytes=65536 max_frames=16 ready_only=1`；原本Npcap ingress local drops=0，未开启弱网修复。原Windows各场景raw CPU+日志 A ZIP`14721998486`/B `14722176818`，跨job收据`14721893863`/`14722161634`，结构化证据`docs/evidence/M0/PLAN029-H2291-FULL-WIN-ARM-NPF16-20261122.json`。
- H2291候选虽然 A/B 原业务和原Stop成功，旧H2290对应跨VM绝对吞吐/CPU/P99不同，不能说H2291提高性能。另发现初始Windows H2291候选 Rust编译比历史旧 DLL除16ready开关外多其它feature组合；即使强行同机换“旧来源DLL”，也不是纯单因素。因此这次**必须在同一Rust产品代码、同一基础feature**下构建两版DLL，只差`h2291_windows_tx_service`；其它条件一概保持。

## H2292最小有辨别力的同机A→B→A′实验（仍是原产品不是裸TCP）
- 原两个不同组a/b，每组三个**实际VM**：Windows2025客户端签名Npcap1.88/Wintun0.14.1 + 原编译GoTLS exe（原c5066db...真实SHA校验）＋该组唯一ARM64 kernel relay＋另一ARM64原GoTLS/Rust AF_PACKET wan0/TUN server。两组相同真实原Wintun到ARM Rust TUN内层4TCP×25s + 160小TCP、0ms0%外层原内核loss，源锁source/group/run、原证书和routeKey/真实driver+owned Stop。
- 同一Action**一次 Windows builder**用相同Rust HEAD（唯一完整产品源码）及固定基础`m0_v4_embedded_go,m0_v4_probe,m0_fec2_owner_probe,fec2_product_record`分别编译default-off Windows DLL与加`h2291_windows_tx_service`的候选DLL，两版都运行Win32原Npcap真实AB测试、原PE ABI与SHA256有效。两版本Windows真实DLL manifest都为当前SOURCE；两个真实Windows VM仅下载这一套合并构件，原GoTLS exe不重编、不更改，不再复用旧c506版Rust DLL造成feature混杂。ARM原GoTLS/Rust源码差异仅限Windows-only特性，先校验再复用原二进制，一次跨两组的源认证。
- 每个实际Windows VM**同一Runner**依次三次重新启动完整GoTLS/Rust客户端（不重复驱动安装/WSL2/NAT/ARM VM）：原默认DLL A → 候选DLL B → 同原默认DLL A′；每次原TLS认证、签名NPF/Wintun内核链路、原真实ARM TUN TCP/160echo/真实CPU线程采样和完整原WAL Stop，才允许切DLL。同一个ARM64 server VM常驻真实原GoTLS/Rust server，同一个内核relay常驻原netem/port；ARM真TUN内核TCP应用每一腿独立启动并且原UDP负载真启动/真Stop，三个arm结果独立归档。
- 为避免“client开始下一腿但ARM仍在复位”的夹具误判，在原relay UDP4789认证控制面增加 **仅H2292 opt-in** 的真实ARM源地址、原控token、顺序stage ready状态，Windows仅在其组ARM已公布对应A/B/A′阶段后开始新TLS/TCP。该控制面不触碰原443业务/Npcap，**不代理业务**，不产生假ACK/重复密文，不影响原产品批次。组间token与身份不同，任意越序/跨组/无packet FAIL CLOSED。
- 原TCP数据双端每腿真实收字节、吞吐goodput、p99/p50、160echo、CPU秒/实收GiB、Rust TX/RX OS线程下界、relay tailscaled/最热核、packet drop、每腿原WAL/驱动清理及业务原Go TLS证书都须报告，比较 B 相对 (A+A′)/2 的业务吞吐、Win CPU秒/GiB、P99；不能仅选漂亮组、不能拿H2290旧Action不同VM做数值提升。H2292先产原业务**同VM三腿证据**；只有两个组三腿完整、候选同时改善吞吐和CPU、且P99不恶化，才进入安全默认设计考虑；否决则保留H2291候选feature默认OFF，继续查实际Npcap DPC/WSL2与ARM RX瓶颈。
- 后续用户目标仍为完整原Windows+ARM **双向200ms 1%/5% loss，FEC2 off→on→off** 与真游戏/TCP p99、内核本机zero-drop/少HOL和原Stop，029整个包未完成，原PR#68 Draft。不再做裸Winsock夹具竞赛或盲加本机queue。

```feature-impact
{"kind":"none","reason":"H2292 only uses test-only original full signed Windows/ARM products and default-off H2291 trial feature, source-matched two real Windows Rust DLLs, authentic three-generation GoTLS/Wintun/TUN/owned Stop. No default app configs or Go/ARM product modification."}
```
