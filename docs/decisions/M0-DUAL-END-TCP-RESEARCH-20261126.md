# M0 双端可控 TCP / Rust 传输引擎研究记录（2026-11-26）

状态：研究提案，不是施工授权、协议变更或性能验收。RouterOS 分支记录，main、experiment/m0-linux-tcp-splice 与既有角色分工不动。用户提出双端自控 TCP 的最终形态，强调 TLS1.3 建链、外层 TCP-like、稳态 TLS-like 内承 FEC。现有 TLS_HANDSHAKE_CONTRACT、FEC_V2_BALANCED、MTU_CONTRACT 与 PROJECT_CHARTER 仍是实现契约；未擅自解除既有认证、完整性、隔离、MTU、Stop、一次外层机会修复、禁止旧 M2 Receipt / 独立反馈控制器等边界。现有 Off/Fixed/Auto 与 Game 模式不因这次概念描述被静默变更。标准 TLS1.3 冷握手与 TLS-like 稳态必须区分，不声称稳态是标准 TLS 字节流或不可识别。

## 已验证事实与候选源码

- 原 Linux splice 只在隧道侧内核 TCP socket 设置 TCP_CONGESTION，Rust epoll/pipe/splice 搬运两个原生 socket；没有自主 TCP 算法。见 M0-LINUX-TCP-SPLICE-20261125.md。
- CHR 5.6.3-64 容器 BBR ENOENT、BTF 缺失/枚举 EPERM、普通 BPF map 成功；没有已验证的内核拥塞算法注册途径。gVisor BBRv3 参考 fork 9b14a44348f259003600d98cdb4dbd57a8302ca7 独立弱网真实 TCP 512KiB 通过，与同栈 CUBIC 单次独立对照分别 4.68/19.97s；不是配对性能资格。实际 WBD Normal+DNAT+Go sidecar BBR clean/loss、同栈 CUBIC loss 完整九 TCP 与 UDP/Stop 通过；原 NAT loss 两 reset 失败。证据 docs/evidence/M0/20261126-ROUTEROS-WBD-BBR-SCOPED.json；CHR free 限速。Go sidecar 拥有额外 bbrtun、用户态 TCP sender/receiver、两个 io.CopyBuffer 与内核出口 socket；不是 Rust 原生 BBR。
- 首选评估 pktkit-rs v0.1.12，MIT，精确 SOURCE 836ae122e150de50a309c7f1703adb364e13d4c9。GitHub API 查阅 Cargo.toml、src/vtcp/mod.rs、conn.rs、segment.rs、sendbuf.rs、bbr.rs、interop/README.md、benches/hot_path.rs、CI。vtcp feature=[]、不需运行时或额外依赖；Conn 接收 Segment，accept_syn/handle_segment/tick/next_deadline/read/write/close 等由外部驱动，无后台线程。BBRv3 draft-06、CUBIC、rate sampling、SACK、RACK/TLP、PRR、RTT/RTO、窗口缩放、乱序重组、ECN、pacing、TCP_INFO 等有实际源码。项目较新、社区/生产证据少。CI 44655516619 同 SOURCE 的 QEMU Linux interop、tests、bench 与 MSRV job 为 success；不是 WBD CPU/吞吐资格，也没有独立复跑。源码证实 Segment.payload Vec、parse to_vec、marshal Vec、Conn outgoing Vec<Vec<u8>>、sendbuf Vec、发送/重传 to_vec；框架 zero-copy 宣传不能归到整个 TCP 热路径。Rust 2024/MSRV1.89 vs WBD workspace/build script 固定1.85.1，先评估独立候选或有限兼容移植，不擅自改全局工具链。仅复用 vtcp，不引入 slirp/vclient 的线程/锁框架、额外隧道、密码实现。
- 备选 xray-smoltcp/smoltcp：SACK/缓冲/代理方向参考，未验证现成 BBR；bbr crate 0.2.1 仅算法，可做独立对照，不是 TCP 栈；Demikernel/Catnip 只作 I/O/批处理架构参考。未完成这些备选的完整源码/许可证审计或本地基准，不作为选型已定。所有第三方来源以实际许可及 pin 为准。
- 参考链接 https://github.com/KarpelesLab/pktkit-rs/tree/836ae122e150de50a309c7f1703adb364e13d4c9/src/vtcp ; https://github.com/KarpelesLab/pktkit-rs/actions/runs/44655516619 ; https://github.com/adios-404/gvisor/blob/9b14a44348f259003600d98cdb4dbd57a8302ca7/pkg/tcpip/transport/tcp/bbr.go ; https://docs.rs/bbr/latest/bbr/ ; https://docs.rs/crate/xray-smoltcp/0.14.0/source/XRAY-PATCH.md .

## 三种不同架构

A 原 IP 隧道 / 单侧 split：客户端 OS 仍控制 upload，服务器可控制 download；仅服务端自有端点并不能双向自主 CC。只给现有转发包调整 pacing 不能接管其 TCP 状态。

B 双侧 split、保持当前隧道数据格式：app OS TCP <-> client local virtual TCP endpoint <-> 双端自有中间 TCP endpoints（标准 TCP/IP segments 作为现有 FEC 源业务）<-> server origin kernel socket <-> origin TCP。实际上三段连接，不是两个端点同时篡改同一条原端到端 TCP。客户端透明接管 app TCP 后，需要建立与服务端对应的中间连接，原目标/会话映射、半关闭、RST、流控、失败传递均有明确语义；在已认证会话内沿既有 inner IP path，不改变现有 outer TCP-like/TLS-like/FEC 或认证/MTU。两端在长 RTT 中间 TCP 各自控制发送 BBR/CUBIC/ACK、SACK、重传。第一阶段只在 Normal 可选实验，UDP、其他模式仍旧。跨端协商/兼容细节需专项确定，未授权上线。复用成熟 TCP 状态机，可直接与真实 OS TCP 互操作，比立即另造可靠协议更有可测性。

C 长期候选：本地 app TCP 端点 <-> 双端按业务流分开的字节传输 <-> origin kernel TCP；中间不必携带完整 TCP/IP 头，可研究轻量流标识/offset/信用，独立流有序、不跨流 HOL。若移除中间 TCP，则残余丢包下可靠字节交付、去重、重排、流量控制和关闭语义仍必须由某一层承担；FEC 有限冗余不能保证任意丢包下可靠，现有最多一次机会修复也不保证。不能在保持当前红线的名义下悄悄添加外层持续 ARQ、旧 M2 Receipt/独立反馈控制器或把外层 ACK 当业务确认。C 是单独研究假设，涉及新内层语义/互通/控制面，须明确决定、定义接收确认语义与成本收益后才实施；不推荐作为下一步。

## 性能与控制边界

- 在 B 中隧道两端的发送器各自拥有真实 ACK/交付速率采样、cwnd、pacing、RTO、SACK/RACK/重传和流控；客户端/远端应用自己的 TCP 仍是原生。业务 TLS 不需解密。分段 ACK 仅表示代理端点接收，不表示原业务服务器/应用收到；有界背压和错误传播必需，不能声称保持端到端 TCP 可靠语义或进程失效无损。
- 稳态 Rust 数据面只保留必要原 TUN/Wintun 接口与真实驱动；在原认证解密/FEC 恢复后的 IP 分流处接入 TCP owner，回程生成的包交原发送/FEC。避免第二 TUN、每包 Go/Rust FFI、额外线程、双重拷贝和忙轮询。单连接 owner，按已有并行瓶颈决定是否分片；合并就绪处理但不等凑批，timer 驱动而非全表扫描。缓冲区载荷引用/生命周期与 ACK 回收是优化重点；不承诺加密/FEC/驱动/内核 socket 绝对零复制。
- TCP 内层重传和外层 FEC/一次机会修复属于不同层；先保留原 FEC/repair，测真实 ACK、残余损失、恢复时延、实际总线速开销；禁止以外层 ACK/恢复统计冒充业务交付。每条业务的独立拥塞窗口不等于整个隧道总容量；多流争用同一瓶颈时，首先量化实际队列/小流 P99、CPU、总发送预算、公平性。任何统一拥塞调度候选必须不与既有控制器重复争抢，单独验证，不复活旧 M2。
- 800Mbps x 400ms RTT 的 BDP=40MB（十进制）；窗口和实际留存按测量/需求增长，受真实资源约束，不给每流预分配几十 MB。FEC 冗余与头开销降低可用源速率，如满组125%冗余，1Gbps线路理论源上限444Mbps（尚未扣头/repair等），BBR 不能消除物理约束。内核基线若不是同一算法版本、同一实际条件，不混成栈效率因果结论。
- 性能可能接近乃至在 WBD 全路径超过 Linux splice 的条件：省去额外内核往返/重复解析/用户态拷贝的成本大于自有 TCP 的逐包状态与定时成本。Linux GRO/GSO/TSO、缓存和成熟重传仍是强基准；不能从 Rust、zero-copy 宣传或 CHR 结果推导达标。建议目标阶段：原 Linux splice 70%/90%/100% 吞吐、后续单位 CPU 不高于基线；只是待验证工程目标，不是承诺或现有硬门。

## 建议顺序（非施工授权）

1. 保存 Go sidecar 功能参考与原 Linux splice 对照。普通 Linux 同 runner 隔离环境验证 pinned pktkit standalone，真实 Linux 对端、半关闭/完整 bytes/hash、BBR/CUBIC、0/1/5/15/30% 和 400ms 代表工况；比较相同算法尽可能相同版本、分别报告本机单核 ceiling 和实际 WBD CPU/GiB、延迟。先看可行性与瓶颈，容量不足标注，不刷矩阵。
2. 服务端原生单侧接线，保留旧 wire/UDP/FEC/客户端，复用 owner；用 profiler 定位 copy/alloc、scoreboard、timer、I/O，局部去除成本。和 Go reference/native splice/NAT 独立比较，真实 x86/ARM/Windows 代表按范围验收。
3. 客户端透明 split 与双端 middle TCP，先 Normal，维持现有外层和 FEC。上行/下行、同一隧道大小流混合、两个方向并发、多用户、Stop、重连、失败传递。只在成效成立后扩大模式；无跨流 HOL、真实 first delivery、CPU/内存及稳定性联合验收。
4. 若中间 TCP/IP 开销或重复恢复确为主要瓶颈，才研究 C；先明确新内层语义、协议红线、失败模型与可回退边界。无直接实施授权，不改现有协议及默认值。

未运行 pktkit/WBD 实验，未实现双端 TCP；本次只有研究记录。原分支/main 未修改。

## Windows 下载反向 ACK 与架构选择（同日补记）

只读复核 experiment/m0-linux-tcp-splice HEAD 26b11e2da236e909b73f461964c52d5a86d42dca。H2479 run45787098527 已有验收 JSON，H/I 两台9V45，MSS1049；裸250M ACK/segment 3.458/3.455%，WBD250 49.988/50.671%，实际237.34/225.97Mbps，6000样本除首个外全推进，无SACK。裸650M 1.695%/1.695%，WBD650 70.951/75.908%，实际243.98/317.53Mbps，H 5999相等ACK，I 5999推进，均6000 SACK，+25s重传111.6/126MB。ACK比值基于sender ss segment delta，不是严格线包比例；采样仅server存活ACK，非逐包因果链。所有clean_candidate=false。RSC ON/OFF/恢复未改变裸ACK比例，RSC统计缺失，发送TSO/GSO、虚拟化/其他聚合仍待证。H2480 run45791400655 八台CPU跳过，唯一E 9V45 WSL准备失败，无有效TSO/GSO干预；不声称阴性。H2478记录TX kernel约80–86% TX CPU，D copy source_wire 287528941B vs control 726534B、repair893172B，支持主要反向业务源记录而非外层ACK洪泛，但字节不能代替包数或CPU归因。此次查分支已验收文档、源码与H2480 job logs，未独立复算H2479原始artifact。参考 https://github.com/lly8666/wbd-next/blob/26b11e2da236e909b73f461964c52d5a86d42dca/docs/devlog/M0/20261126-H2479-H2480-ACK-OFFLOAD-DRIVER-RESEARCH.md ; https://github.com/lly8666/wbd-next/actions/runs/45791400655 。

现状：Windows NPF RX -> Rust鉴权/解密/FEC -> Wintun TX写入Windows TCP -> Windows产生内层ACK -> Wintun RX/TX worker -> Rust业务封装 -> NPF TX。外层TCP-like ACK/SACK另行处理，不能混为内层TCP ACK。v4_windows_native_runtime.rs 当前一Wintun、一NPF RX、一NPF TX，Wintun writer属RX、read属TX；原TX batch/ready fairness/repair仍有效。正常每2 MSS ACK不等于错误，650M高压真实缺口/乱序须另外定位。仅替换server BBR无权改变Windows接收ACK；仅双端采用默认TCP delayed ACK也未必减少中间ACK PPS。不能删/假造内层ACK、丢SACK或通过延时凑批掩盖丢失；外层确认仍只作既有提示。

结构候选：先服务端原生pktkit，随后客户端TUN透明分段：Windows本地app TCP <-> Rust本地端点（Windows ACK在本地消费）<-> 自有middle TCP双端（仍沿原inner IP/FEC）<-> server出口socket。把Windows ACK与远程ACK解耦；middle ACK由我们真正接收数据后生成。默认RFC delayed ACK为首轮基线；优化仅凭同状态、真实累计确认、准确窗口/时间戳/缺口与SACK语义，先利用已就绪处理、合法piggyback等，不人为等待。若要独立更稀疏反馈或ACK批量载体，需两端明确约定与新内层语义研究，不是普通TCP透明ACK过滤；不能恢复旧M2/外层持续ARQ。B方案保留Wintun本地TCP交互，尚有内核成本，但本地ACK不再经加密/FEC/NPF TX，middle ACK还存在，实际降幅待测。C方案WFP ALE连接重定向到本地原生socket（现有WFP过滤不代表具备重定向），通过IOCP/批量socket I/O接入自有middle TCP，可让选定TCP绕开Wintun包级往返；UDP及其他IP仍Wintun。需要验证应用覆盖、原目的地址、连接关闭、环路、驱动权限/签名/许可，不自行部署或更换驱动。现有标准签名Wintun保留为近期基线；已有H2479研究的NBL就绪批量和真正RSC作为独立对照，不假造超MTU IP包或NDIS元数据。物理NPF收发仍有下限；即使自有TCP也不能免除外层反馈或驱动内核开销。

数量级计算：假设实际600/800Mbps业务、MSS1049、满段且每2段ACK，约35748/47664 ACK/s；若可达到裸250 ACK比3.45%则约2467/3289 ACK/s，仅是假设量级，不是可用策略/性能承诺；裸低比可能来自卸载单位，不能照搬。优先直接测同runner 250M健康和650M压力两点，逐边界统计Windows本地TCP ACK、middle TCP ACK、外层ACK-only、NPF实际accepted PPS、FEC/repair、源有效字节、前向首次交付/残余缺口、TX/RX kernel/user CPU/GiB和真实小流P99。用相同内层CC/MTU/源供应、已验证的对照，区分分段/ACK变化与前向RX瓶颈；后续再测WFP架构是否值得。没有性能PASS或新施工授权，本次仅研究记录，未改splice原分支或main，不抢其在途H2480。
