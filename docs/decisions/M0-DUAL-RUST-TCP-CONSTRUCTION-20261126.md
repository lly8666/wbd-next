# M0｜双端原生 Rust TCP 与 Windows 简化施工方案（2026-11-26）

任务 M0-DUAL-RUST-TCP；责任人 M0；用户明确授权按以下两阶段连续实施。唯一工作分支 `experiment/m0-dual-rust-tcp`，从 `experiment/m0-linux-tcp-splice` 精确 HEAD `26b11e2da236e909b73f461964c52d5a86d42dca` 创建。该指定基线覆盖常规从 main 开短分支的规则，不把 splice 分支全部祖先自动合入 main。main 仅登记任务/恢复入口；原 splice PR78、RouterOS PR79 保留历史与独立证据，不关闭、不覆盖、不继续重复旧包；此前在途若出现新结果先结算事实。先比较 main 与实验差异；最终集成只取经选择及复验的能力，避免误带已拒绝的实验。当前未施工、未测新源码。

## 0. 用户决定、硬边界与取舍

- 先 Linux 客户端和服务端双端接入 pktkit 原生 Rust TCP，x86_64 与 ARM64 都要原生运行。与原 Rust 收发、认证解密、FEC、原生业务交付及生命周期无缝衔接；允许有依据的重构和删除，不做 sidecar、第二 TUN 或 Go 逐包接口。旧 Linux 业务 TCP 透明代理只在对照阶段保留，确认性能相当且真实功能覆盖后删除旧实现及无用配置。
- 第二阶段才 Windows：同一 Rust TCP 核心；简化 Direct/Tunnel，取消 FakeIP 域名映射/旧功能；DNS 返回真实地址，按连接实际目的 IP 判定 CN 直连、非 CN 隧道，TCP/UDP 规则一致。解决下载 Windows 内层 ACK 导致的反向 TX 开销，不牺牲真实交付、弱网重传及小流延迟。
- 用户指定：TLS1.3 建链、TCP-like、TLS-like 是红线，既有 TLS_HANDSHAKE_CONTRACT 实际为成熟 TLS1.3 标准握手；外层格式、认证、加密、FEC、已有模式、MTU、generation、原密文一次机会修复均保持。此授权仅更新内层业务 TCP 实现与 Windows FakeIP/分流功能，不授权改变外层、重造持续外层 ARQ、旧 M2 或 TLS。业务 HTTPS 不解密。原产品标准握手、包格式、配置密钥及服务器验证不动。章程原“默认不自造TCP栈”在本授权范围内由明确复用 pktkit 取代；旧 PLAN029B FakeIP 兼容保留要求在第二阶段由用户明确删除覆盖，其他章程保持。
- 禁止任何防御性开发：不增加无事实依据的防御措施、假想回退、过渡永久双栈、额外控制器或通用架构；既有协议正确性/所有权/认证及真实流控是硬门，不删除。大胆施工、全面独立判断、不迎合、不违心、不钻牛角尖。目标是全链路业务效率，不是 Rust 代码行数或局部 ACK 数。

## 1. 研究起点和可复用证据（不是新分支资格）

- pktkit-rs v0.1.12 MIT，审查时精确 commit 836ae122e150de50a309c7f1703adb364e13d4c9，[vtcp源码](https://github.com/KarpelesLab/pktkit-rs/tree/836ae122e150de50a309c7f1703adb364e13d4c9/src/vtcp)、[上游CI](https://github.com/KarpelesLab/pktkit-rs/actions/runs/44655516619)。有状态机、BBRv3、CUBIC、SACK/RACK/TLP、RTT/RTO、rate sampling、pacing、send/recv buffer 与外部 tick/deadline，不需后台线程。实际 Segment/parse/marshal/send buffer 存在 Vec 与复制，不能宣传零复制；Rust1.89/edition2024 与 WBD 1.85.1 固定工具链需核对，先选择最短可维护的兼容移植或有依据的工具链升级，真实全目标构建/打包验证；保留MIT许可与来源pin，不浮动依赖。优先复用 vtcp，不引入第三方 TUN、runtime、加密协议。若发现关键算法问题先修有证据的实现，不盲信项目宣称。
- 原 Linux splice 以原生内核 TCP_CONGESTION + epoll/pipe/splice 实现单侧 split。参考 [RouterOS研究汇总](https://github.com/lly8666/wbd-next/blob/34820438a495af7fadba92dcc7e4401278c23850/docs/decisions/M0-DUAL-END-TCP-RESEARCH-20261126.md)、[WBD BBR限域收据](https://github.com/lly8666/wbd-next/blob/3ace4400ad63817b6ef7f313a955f21e711ed5dd/docs/evidence/M0/20261126-ROUTEROS-WBD-BBR-SCOPED.json)。Go gVisor BBRv3 sidecar 真实 Normal DNAT 可用、额外TUN与复制不是正式架构；CHR免费限速，不作吞吐资格。
- 原 splice H2479/H2480 [研究日志](https://github.com/lly8666/wbd-next/blob/26b11e2da236e909b73f461964c52d5a86d42dca/docs/devlog/M0/20261126-H2479-H2480-ACK-OFFLOAD-DRIVER-RESEARCH.md)：250M WBD反向ACK/segment约50%，裸TCP约3.45%，MSS1049；前者健康ACK推进，不是可删重复ACK；650M大量SACK/重传/交付下降，真实缺口另因；TX约80–86% kernel CPU；H2480 run45791400655 无合格干预（CPU gate/WSL准备失败），不能宣称卸载因果。旧main cursor H2447 已明显滞后于 H2480；恢复时主动查分支和Actions，不靠旧游标。旧结果不修改，原包由本新任务取代而非虚称旧任务全PASS。
- 源码入口：crates/wbd-engine/src/v4_embedded_go.rs (Linux original TX/RX/shared TUN); v4_linux_tcp_splice.rs 与 r0/go_overlay/internal/v4productcli/{linux,tcp_splice_linux}.go (旧代理); v4_windows_native_runtime.rs / v4_windows_game_native_runtime.rs / v4_windows_native_split.rs / v4_windows_native_tcp_direct.rs；wbd-platform/src/{linux_raw_carrier,windows_native_io}.rs；共用 v4_client_* 与 runtime/memory。以上为起点，接班时实际 HEAD 为准。

## 2. Linux阶段：公共 TCP 核心与双端实际产品

架构：app OS TCP -> 原客户端 TUN -> Rust 本地 TCP 端点 -> Rust middle TCP sender/receiver -> 现有内层IPv4业务入口、AEAD/FEC/RAW -> 服务端原认证解封/FEC -> Rust middle TCP端点 -> 原生出口socket -> origin。三个 TCP 区段有各自确认；下载和上传的中间 sender 均由 Rust BBR 控制。应用侧和出口仍标准TCP，现有中间TCP/IP段在已认证会话的原内层数据通道承载；不另造外层或新增私有TLS交换。明确原始目的、连接标识、双端角色、握手/关闭/错误、generation 归属，使用现有认证及地址约束；双端同时升级的产品约定在文档/配置中明确，不假装与旧端点无条件互通。必要内层语义设计限定于用户授权，不能触碰外层红线。非TCP/UDP仍现有路径，现有不经代理业务、DNS和普通TLS访客独立。
 
### L1 接入和打通（一次完整能力增量）

1. 审查 pin/license/MSRV 与发送队列、接收队列、计时和 BBR 交付采样，沿实际源文件决定依赖/有限移植。建立公共 Rust TCP flow owner（建议 wbd-engine 独立模块，pktkit vtcp 为核心），明确每连接唯一所有者、共享 payload 生命周期、连接地址与 generation；外部传入实际事件，返回可发送段及下一个 deadline。避免每流线程、全表轮询、重复编解码。先跑定向源码测试、真实 native TCP 对端互操作（SACK/乱序/half-close/FIN/RST/窗口/真实ACK），不是独立demo替代产品。
2. 一批接齐 Linux client TUN入口分流、本地端点与 middle 端点、server接收和出口非阻塞 socket I/O、回程业务段直接进入现有Rust原发送owner；不要先写TUN再读第二TUN。按真实 owner/背压改造 TX/RX、ready queue、socket写读、定时器；真实TCP ACK表示该段接收，不代表origin应用交付，保持半关闭及失败传递；不把外层ACK/repair统计当中间TCP ACK。
3. 初始 Normal 原生双端实际业务、旧基线对照入口及 Stop；再按受影响的 Normal Fixed/Auto、Game2/4及其FEC模式实际接线和必要的独立UDP、小流并发、多租约、换代/重连/Stop回归；只测真正公开入口。保留成熟冷Go TLS、MTU预算自动、现有 RAW接口；一份公共Rust逻辑覆盖双ISA。配置/CLI/装配/功能卡同步更新，临时对照入口只服务阶段测量，不成为永久fallback。

### L2 性能优化与确认

- 在普通Linux原生x86_64、ARM64 runner验证，复用原三runner/namespace真实网络夹具和 glibc2.31 双ISA构建。禁止用CHR免费版、模拟/交叉编译代表性能。冻结原splice A 与候选 B 精确SOURCE、manifest/hash；同机同配置、独立场景顺序 A/B 或 ABBA，吞吐量方向/源供给、真实RTT、MSS/MTU、FEC、拥塞算法版本和路由一致或明示差异。算法版本不同不能把差异单纯归因于用户态/内核态。
- 首轮零注入损伤及高RTT代表（400ms，1%/5%损伤优先）真实单流双向、实际容量内；按已知性能目标和容量扩到大下载/上传、并发小流、较重损伤（15/30%在相关档位且有容量时），不机械全矩阵、不刷seed。测试实际 application receive/hash、首到/尾延迟、CPU s/GiB及方向/用户态内核态、PPS/重传/ACK、RSS与queue、前向首次交付和Stop。按 TEST_PLAN 一Action一性能场景、同job顺序；有真实功能证据后再性能，失败定位最有价值的瓶颈。
- 先剖析实际 copy/alloc、热表/ACK scoreboard、timer、epoll/socket I/O、锁/唤醒、Rust<->内核往返；共享原内存池及 payload，ACK后回收，批处理已就绪包、不等凑批。只改有实测成本的关键路径；不先上通用框架或擅自改编解码/外层。
- “性能差不多”由同环境证据判断，建议工程判别带（非用户另立硬数值）：代表场景有效吞吐达到旧splice约90%以上、单位业务CPU成本不高于约110%，首到/小流P99无实质退化，丢包/负载下不引入新失效；结合实际测量噪声及旧路径的算法/功能不等价解释。接近阈值以真实成对样本决定，不靠换环境选好结果。较低 CPU/更高有效交付优先，不为了机械门限无限微调。未达到或无合格对照则不能删旧代理。
 
### L3 退役旧透明代理

L1/L2 在双ISA实际覆盖并确认与旧方案性能相当后，由M0在同工作包中删除旧 **业务 TCP** 透明代理相关实现：Linux Rust epoll/pipe/splice owner、旧 TPROXY/NAT listener、FFI/配置项、对应专用装配/夹具与功能卡，替换实际CLI/帮助和引用；不保留永久两份实现。已冻结旧二进制用于后续对照，历史文档与证据不删。特别区分普通TLS访客decoy/冷握手字节转发和其他仍在使用的通用socket能力，不能因名字有splice误删。实际删除后重新编译双ISA、跑公开入口代表功能、原生Stop和关键性能复核；根据治理分阶段集成，先核 main 是否包含不同已验修复，避免把旧实验祖先整体带入。

## 3. Windows阶段：共用 Rust TCP 与简单真实IP分流

### W1 接线与删除迂回代理
- 使用 L 阶段公共TCP端点/状态机，现有一Wintun session、唯一Wintun writer、已有NPF RX/TX owner；Windows平台层仅处理设备、等待/事件及原生 socket I/O，按CPU证据选择调度。TUN包进入统一连接分类：TCP本地状态机消费，Direct原生物理socket，Tunnel交中间TCP；UDP维持原生数据报直连/隧道。不要另建WFP ALE redirect、第二Wintun/sidecar、逐包Go/FFI；保留现有真实驱动、owned路由/DNS/Stop与必要OS配置。旧 synthetic /32、借Windows内核TCP listener、反向NAT/邮箱与专用代理机制在替代通过后删除，只删实际无用部分。保留原生物理出口 Winsock 与合法系统网络接口。
- Windows支持范围按当前产品及实际签名驱动夹具，x86_64 Windows真实应用 -> 原Linux服务端（x86/ARM各有实际代表）；GUI、CLI、配置、签名Wintun/Npcap原入口不绕开。Linux客户端分流是否同步复用可根据产品范围决策，不额外扩权；Win物理IO替换 XDP/WinDivert 不是本阶段必做项，只有证据显示现接口为根因才另作对照，不能把换驱动当ACK解决。

### W2 真实IP分流，正式删除FakeIP
- DNS回答真实A/受支持的AAAA，按每条真实目的地址的CN CIDR匹配分类，不按域名名单、FakeIP、DNS查询名推测；CN公共地址直连，非CN公共地址走隧道；直接输入IP同规则。CNAME、多A、DNS缓存/TTL、每连接实际选择的地址，不用Fake映射或域名驱动路由。保留既有本地LAN、环回、链路本地、隧道控制端点及DNS自身系统路由职责（这些不是公网站点地理分流），IPv6按实际已支持能力，不假称未知地址族已通。CN数据表采用现有可信可固定来源的前缀集合，记录版本/许可；不按域名后缀猜国家，不对未匹配公网地址直连。DNS解析路径沿现有真实可用解析器，明确查询路由独立于答案地址分流，不新增复杂域名策略；如果现有DNS路径不能返回可靠真实地址，修实际入口，不恢复FakeIP。
- 真实流按首次目的匹配固定出口，数据集更新仅新连接使用。删除 FakeIP池/映射/journal、合成地址分配、旧专用配置/GUI/测试/文档功能卡及不再需要的域名规则；旧配置文件采用明确一次迁移或清晰提示，清掉本项目拥有的旧FakeIP路由/DNS状态，不静默假装仍支持、不保留永久双策略。实际直连/隧道 TCP/UDP、多个真实DNS地址混合及已知回归、重连/Stop验收。

### W3 大下载ACK和TX效率
- Windows本地OS TCP ACK由本地Rust端点消费，不作为业务包再次封装穿越隧道；真实middle TCP反馈仍由两个端点管理。优化仅以真实接收状态与正确累计ACK/窗口/SACK及现有就绪批次为依据，保持 TCP 正确性；不简单丢弃ACK/伪造确认/隐藏缺口、不人为等待凑批。不能仅用Rust状态机存在证明ACK下降；650M高压前向缺口和驱动容量独立判别。
- 同机对比旧 Windows + 原 splice 与新 Windows + Rust 双端，先250M健康、650M压力代表，按实际供给、RTT/MSS/FEC一致，区分本地ACK、middle ACK、外层ACK/control及NPF实际PPS；计量TX/RX kernel/user CPU、有效吞吐、首到、小流P99、重传和前向首次交付。目标实质降低跨隧道ACK和TX每GiB成本且不降低真实交付/延迟。裸TCP低ACK比例不是可直接照抄目标。若降幅不足，定位实际端点、调度或I/O机制再做有区分力的改造，不靠假阳性。禁止用仅本地消耗ACK就宣告物理TX问题解决；功能/性能都要真证据。

## 4. 治理与阶段交付

按 AGENTS/GOVERNANCE/TEST_PLAN、main registry 与唯一M0 cursor；用户指定起点为分支例外，不另造治理系统。不抢原 splice 已有在途任务、不复活旧包；初始计划先登记 main，创建精确分支，首实质WIP push 后开同一 Draft PR。工作包内 L1→L2→L3→W1/W2→W3，阶段完成自动继续，无需重复授权；有独立任务可按实际依赖并行Actions但不委派其他agent。允许在真实收益支持时调整阶段内部实现，不扩大wire或物理部署权限。

每次接班刷新 main/实际分支/PR/commit graph、Actions run/attempt 与manifest，承认文档和游标可能陈旧；核实当前事实再施工。运行验证仅Actions，按既有批次intent/source锁；一次构建每ISA/平台复用产物，真实性能同VM顺序；保存历史FAIL/NOT_RUN，不虚报。S实质提交、H独立cursor更新，阶段证据及功能卡及时提交，原记录保留。整包退出：Linux两原生ISA双端完整业务、受影响模式和Stop、同机性能对照达相当水平后删除旧Linux业务splice；Windows共用Rust端点、真实IP分流及旧FakeIP/中转退役，下载ACK/TX CPU与交付同机对照；配置/GUI/功能卡/证据一致，未测不晋级。按计划阶段集成，旧失败与物理资格独立。。无物理机测试授权，不默认部署。首个 next_action 是 Linux 双端原生 pktkit Normal 从真实 TUN 到实际origin 的完整可运行能力（含双ISA编译/运行及真实UDP/Stop），非反复做独立demo或只加接口。
