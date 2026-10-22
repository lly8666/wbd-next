# Windows客户端→Linux服务端：先打通产品，再扩网络矩阵

2026-10-22用户后续授权的执行收口。审阅main `1857e781dc3d5d1acb7a99d8d7f588773585a4e4`，产品最新相关SOURCE `a22c4e09baf7c42a39b4eab1d7c3febffc5a6836`。这是待执行计划，不是已接通声明；并入PR22，由当前M0集成并更新既有任务/next_action，不修改其他活跃作者的cursor。场景/数学门继续读[矩阵](NETWORK_MATRIX_20261022.md)，定位与修复前复习继续读[手册](NETWORK_TRIAGE.md)。

## 1. 当前真正卡住的地方

- Action39720987395五模式6/6成功是**组件范围**：原Go认证TLS、Rust RS16、真实Wintun恢复/Stop；不是Windows公开CLI连Linux服务端的持续流量。Action39720486837的双向10M是Winsock本机loopback，不经过产品。
- `crates/wbd-engine/src/v4_windows_owner.rs::wbd_m0_win_owner_v4_mode_capabilities`仍返回`supported_modes=1, authenticated_lanes=1`。公开Windows只支持Normal，不能只把mask改31宣布其他模式完成。
- `cmd/wbd-client/m0_native_v4_peer_windows.go`自带`pending max=256`、满就不读新TUN包、固定750ms重试、8次耗尽报错停止。这套适配策略与共享M2的两次有界修复、真实receipt、fresh独立、10%预算目标不一致。即使无丢包，256个1200B payload在RTT600ms下理想持续上限也只有约4.096Mbps，在RTT400ms约6.144Mbps；混合小包更低。这是该暂存策略的估算，不是产品实测吞吐。
- Fixed/Auto公开发送目前没有完整组形成/partial deadline/parity调度和认证Applied接线；Game公开入口明确拒绝，缺2/4条独立Npcap/TLS lane的真实组合。不要再重复证明底层codec能恢复两包来替代这些工作。
- H244还引用了一条不存在的devlog路径（多了`Rust-`）；实际是`docs/devlog/M0/PLAN024-S764-parallel-shared-RS16-and-Windows-PR21-WinSock-proof-20261022.md`。M0下次正常cursor提交顺手修引用，不单独开启治理工程。

## 2. M0只收一个完整能力包，按三条线推进

**本轮完成定义：公开Windows客户端+公开Linux服务端，真实Wintun/Npcap→原Go建连→Rust数据面→Linux raw/TUN，Normal/off持续双向业务可观测，能加真实内核损伤，Stop恢复自己修改的状态；至少三条独立持续场景产出。** 这是开放大矩阵，不是宣布全产品发布。

### A. 先把Normal/off接到共享恢复运行时

先定向复习`modules/02-RUNTIME`、`04-CARRIER-IO`、`08-RECOVERY`及相关近期修复；追Linux `bridge_v4_linux_client_product.go`/server中的`armOriginalPublicM2Feedback`、`startRustOwnerLoop`到真实Rust owner，核当前接口可复用范围。

Windows保留原Go建连/凭据、Npcap与Wintun/WAL；适配层只搬运真实输入、批量输出、发送完成及Stop事件。优先接共享Rust调度、receipt、Shadow/预算与FEC API；缺接口就补最小平台中立调用，不再在Go另写第二套重传或FEC控制器。不能为了这次接线全面重构所有FFI。

去掉上述256项ACK闸门对fresh的依赖；保留有界I/O队列和明确过载丢弃，不等于无限缓存。shadow淘汰/过期只能Abandoned，不伪造ACK，不阻塞新包；真实I/O永久失败、认证/generation错误仍按现有契约处理。独立包可先到，缺口和普通修复耗尽不能直接变成整连接致命错误。不能仅改256→4096或750ms→更小就收口。对端receipt、late packet与放弃语义一同检查。

一个功能批次覆盖：真实双向首到、缺包后新包继续、ACK延迟超过原256容量仍发新包、缓存过期后迟到、最多两次/持续预算/稀疏额度、Stop。源码未改的旧组件测试复用，不重刷五模式全套来代替本批证明。

### B. 同时搭一个可复制的跨平台Actions环境

**首选候选：一个`windows-2025`测量job，Windows原生客户端 + WSL2中的Linux原生服务端/路由netns。** 它是真Windows/Linux软件栈，不是物理双机，也不承诺宿主能测到500M。先做一次有界环境能力批次再决定是否采用，不把虚拟化研究变成新项目。

官方镜像当前列WSL2，但GitHub不保证嵌套虚拟化的稳定和性能，故必须实际核验：

1. 真实WSL2（不是WSL1/MSYS）、TUN、raw socket、netns/veth和netem模块可用；记录Windows镜像/WSL内核/CPU/quota/RSS。
2. 真Npcap DLL/驱动、管理员权限、可抓发选定vEthernet的以太帧、真实Wintun；仅DLL存在不算驱动可用。Npcap不默认已装。沿用已有获准安装来源；免费安装器没有OEM `/S`能力，不能照抄不存在的静默参数。没有可用驱动/自动部署条件，给明确环境阻塞，不造mock替身。
3. 明确选择WSL虚拟网卡的真实ifindex/IP/MAC/下一跳；若现有`DiscoverPhysicalUnderlay`拒绝合法测试网卡，只补显式、校验身份的接口选择并照常执行owner/WAL约束，不伪造物理网卡收据。网卡名/地址动态发现，不能硬编码某次runner的172地址。
4. 走真实IP/以太帧路径，不用localhost端口转发、SSH TCP隧道、WebSocket中继或流式代理承载被测raw数据。它们会引入另一层有序恢复，改变弱网语义。
5. Linux路由namespace两侧分别施加每方向限速/延迟/丢包，客户端到服务端与反向各只经过一次目标netem。使用路由veth/必要有界IFB，不在应用内部随机丢包代替线路损伤。RST抑制、校验/offload/MTU按已有raw夹具校验；netem传播队列按实际PPS×delay配足，区分随机损伤与队列overflow。

被测路径：`Windows真实UDP/TCP应用 → Wintun → 公开wbd-client/Npcap → vEthernet → Linux损伤路由 → 公开wbd-server/raw → Linux TUN → 真实UDP/TCP应用`。两个方向独立发流，不用一问一答回显代表双向持续业务。

Windows只把声明的测试业务网段导入Wintun，管理/runner/WSL控制通道走原底层。优先使用已有真实配置；若公开产品只有全局接管，补一个明确的测试网段作用域配置，复用同一OS Apply/readback/Stop/WAL，不写假guard、不关闭认证、不伪造全局WFP/DNS通过。全局默认路由、DNS劫持、IPv6/UI验收仍OPEN，放后续专用工况；本阶段收据明确是`SCOPED_TEST_PREFIX`，不冒充全局代理产品。

所有新选项要在CLI/帮助/参数目录留用途和范围；GUI不适用的诊断选项注明原因。无需重做GUI页面才能测数据面。临时安装驱动和Linux tc编排属于夹具，不把产品退回依赖PowerShell网络脚本。

若该hosted拓扑因已证实的WSL/Npcap/权限限制不可用，不连续换image/装一堆模拟器。后备为**已有授权独占Windows+Linux测试机，由一个Actions测量job编排**，或已具备的专用VM对；当前仓库self-hosted runner数量核为0，不能假定已具备。在确认可用机器/凭据受保护和管理通道后才配置，不把密码写入workflow。共享一对机器时串行，不能并行矩阵制造互相争抢；要并行必须有独立环境。公开仓库的自托管仅受信任源码/手动任务可用，不跑任意外部PR。

真实跨地域线路会叠加底噪与时延，实测标明，不能称纯IID或用未校准时钟算单向p99。Linux→Linux夹具可继续提供确定性内核矩阵，但不能覆盖Windows资格。500M能力不足就停止加压并说明，不为达数字重搭实验室。

### C. 最少开门测试通过就立刻扩矩阵

构建与测量分开：同一SOURCE一次构建Windows和Linux bundle，manifest逐文件hash；测量Action下载复用，不每条重编。复用PR21 config/traffic/report/schema，新增Windows启动/遥测、Linux netem和cleanup adapter，不能复制一套统计/恢复理论。

先做一个实际双端功能批次，接着三个独立Action，各双向真实混合包10Mbps、60s（另留合理drain），先off：

- `WL-N0`：0% loss、单向300ms，验证正常flight不因缓存闸门停发。
- `WL-N1`：1% loss、单向50ms，观察实际快速修复与fresh交付。
- `WL-N5`：5% loss、单向50ms，观察预算、残余与p99；后续再按总矩阵扩200/300ms、非对称和高损。

每Action一个场景一个测量job；三条可在各自独立环境并行。环境预检可合并功能断言，不能合并三场性能到一次测量再挑好结果。固定环境准备后先核无产品的生成器/基础路径容量；这个短预检标CALIBRATION，不混入产品性能值。

低负载输入要接近目标，原主矩阵的容量/统计允许带复用，不另造一套更严门。原包内容/generation/真实密文重传/owned Stop仍硬门；只有模型理想值没达到则定位，不宣布安全错误也不刷seed。缺repair字节不能判预算PASS，但不阻止先记录其余真实结果。

两端最少记录：requested/effective、实际注入/首到包字节、p99及统计口径、10ms首到桶、最长空洞、F/R/control字节、放弃原因、raw/TUN本地drop、队列年龄、CPU/RSS/WSL宿主预算、Stop。跨OS单调时钟不直接相减；优先RTT/各端驻留，单向延迟只有已量化误差的时钟校准才报告。WSL vmmem包含Linux开销，不把它与Linux进程CPU重复相加当产品CPU。

Normal门通过即发矩阵中已适用场景；不等待所有功能完成。同一SOURCE结果按实际能力标`OPEN_FOR_NETWORK_TEST`，性能不足是后续优化问题，不自动撤销已证明的互通功能。

## 3. 其余模式加入顺序，不挡Normal

1. **Fixed**：公共客户端真实参数→认证协商→M2 Applied→共享FEC source即时发/满组和partial关闭/parity限时调度→Linux接收。每种实际保护类的k/r_sent有证据；不能仅把blockID每包递增、每组只发source0叫FEC。给双向都丢一个source的真实恢复断言和一条持续样本，再加入FEC矩阵。
2. **Auto**：基于已接通Fixed的反馈和revision应用，现行控制器参数按矩阵修订；先让真实档位变化/有效回执/上下行独立生效，完整曲线调优在网络测试阶段完成，不在开门前追完美。
3. **Game2/4**：实际2/4个独立原Go TLS/Npcap lane及Linux server组合，正确逻辑去重，共享FEC不每lane重复编码；故意断一lane仍交付、Stop能释放所有lane，之后跑Game矩阵。全模式共享底层修复，不能复制Normal临时pending逻辑。

这三项在当前完整能力包内连续推进；已有可测Normal可以消费冻结产物跑矩阵，M0继续无冲突接线。每模式一次真实功能批次，不再围绕同一两包示例连续拆几十次提交。需要独立模块帮助时沿原registry分配一次完整包，不新增工位。

## 4. 本轮不做的扩展与交付

暂不做新加密、新FEC算法、新GUI外观、新发布/安装系统或全面治理改版；不恢复旧Go热路径兼容成本。已有功能真实调用有阻塞才补。安全和Stop硬门保留，不借“快速收口”关闭。

M0收口给一个小表：模式、Windows/Linux准确SOURCE与artifact、真实公开路径、环境能力、三条run、指标/未测、下一步。只将“所有模式一起实现+五阶段全局OS+全部性能”这个过宽next_action改成**当前可验收的一整条公开链路**，不是再次拆成一条断言一张工单。先纠正任务优先级，再开发、执行、留痕，不为了修改叙述无限追加文档。

资料依据：[GitHub Windows2025镜像](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md)、[hosted runner嵌套虚拟化限制](https://docs.github.com/en/actions/concepts/runners/github-hosted-runners)、[WSL真实网络地址/拓扑](https://learn.microsoft.com/windows/wsl/networking)、[Npcap安装能力](https://npcap.com/guide/npcap-users-guide.html)。镜像列出功能不等于本项目已验证；环境批次实际结果为准。
