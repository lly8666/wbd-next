# M0 优先补充任务：修复热路径成本，再继续后续集成

任务 `R1-M0-HOTPATH-COST-024`。用户于 2026-10-16 明确要求先完成本任务开发与同 Actions 对比，再分配后续开发测试任务。它暂时优先于 H102 计划的超 MTU 自动分片集成；原 `R0-M0-V4-PROTECTED-OWNER-COMMIT-023` 的未验硬门继续 OPEN，不因改任务 ID 完成。沿用现有角色/权限/分支/epoch，不新增治理系统。

## 1. 事实、目标与范围

审计基线 `333c1b3f7af6e9a717ba4a6b78bf6a378899f3d5`，原对比 Actions [38920819286](https://github.com/lly8666/wbd-next/actions/runs/38920819286)，证据 [原配对结果](../evidence/M0/M0-023-old-go-vs-rust-same-vm-paired-normal10.json)。旧 Go 两端进程 54.26 CPU-s；新 Go/Rust/发生器混合进程 52.10 CPU-s，其中内核态 43.12s，Rust 两个 worker 38.15s 是其子集。这些人口/拓扑不同，不能宣称 Rust 省 4% 或 30%。双方只投喂 10Mbps，也没有证明最大吞吐相等。

对应实际热路径存在以下可核查问题，不是已测出的各项 CPU 占比：

| 位置 | 当前行为 | 本轮交付 |
|---|---|---|
| `crates/wbd-engine/src/v4_embedded_go.rs` 的 `background_tun_once`，`v4_owner_crypto.rs` 的 budget/seal | 每包先查询 route，再在 seal 内重查 | 缓存、版本化预算；逐包仅内存内验证 |
| `crates/wbd-platform/src/linux_packet_preflight.rs`、`linux_raw_carrier.rs` | 查询 route 创建/关闭 UDP socket，读取 sysfs MTU；raw RX/TX 再查接口 | 建连/变化/错误路径观测，正常数据路径不查询系统配置 |
| `v4_embedded_go.rs` 的两个后台 worker | 反复持共同 registry mutex 执行 owner 工作 | TX/RX 各自拥有可变状态，registry 只管理生命周期 |
| `v4_owner_crypto.rs::submit_scoped_raw_tx` 和后台 RX | TX `Vec::with_capacity(1)`，RX 每轮新建 capacity32，主要逐包 I/O | 复用存储、处理已经就绪的一批包 |
| `start_loop` 中 CPU 计时 | 每轮读取线程 CPU 时钟 | 边界采样，普通热路径无逐包诊断 syscall |

按成功调用链推算每个 TX 包有两次 route socket 生命周期、约五次 MTU 文件读取；这是源码推算，须用有界诊断计数确认，不写成已观测次数。把必要检查放在正确频率，不删除 MTU、generation、完整性或所有权要求。

本轮不改 wire 格式、cipher/FEC 算法、4096/重传预算、批量凑包等待、业务率、地址隔离和冷握手协议；不引入小包优先、AF_XDP、GSO、busy-poll、全面异步框架或新的调度插件。正常路径修复落在原模块和实际调用链，不能只建一个更快的 benchmark 旁路。超 MTU 新功能、Game/FEC 综合性能、完整两端产品和物理测试在后续恢复。

## 2. M0 的施工与并发边界

先核远端 registry、各 worker 实际 HEAD 和 intent。M0 负责共享桥接/接口/主线集成；M1/M4 已有 ready 提交先核来源，若本任务直接依赖可集成，不重做成熟模块。涉及 worker 活跃范围的修改，通过现有正式分配/提交集成协调，不能在 main 与该 worker 同时各改一套实现。

已经在跑的 worker 任务允许收尾和留痕；本任务关闭前不分配无关下一波任务、不启动新的大矩阵。需要 M1/M4 配合修复本任务属于必要依赖，不受此限制。保留原 023、分片、B01–B04 和其他 OPEN 的原证据；新任务进度仍写既有 cursor/devlog/evidence，恢复时不要把旧 cursor 的下一步当作最新优先级。

按以下三个能力批次推进，可多次提交；相关功能反例一起跑，不把每个 getter/包数/参数值单独做一轮交接。先完成明确修复，再跑第 6 节的有限性能集合。

## 3. 批次 A：有效 MTU/路由预算退出逐包路径

### 3.1 数据与所有者

复用现有 FrameBudget/ScopedLinuxBudget、LaneKey、generation、carrier snapshot，补一个单调 revision 即可，不重新发明路由管理器。lane 安装时根据真实接口/route、可信握手 peer MSS、配置上限和 record 开销生成只读预算快照。TX owner 持有当前快照；RX 持有当前设备接收约束。快照至少绑定接口身份、generation、目的路由和 revision；route/ifindex 不是认证凭据。

每包检查 scope/generation、closing、当前 budget revision、实际长度和固定 wire 开销。这些均为内存内操作；steady 不得调用 `read_to_string(/sys/.../mtu)`、`if_nametoindex`、临时 UDP bind/connect/getsockopt，也不得创建查询 socket。正常大小上限不变；peer MSS 变化走新 lane 或原规定的预算切换，不凭缓存放宽限制。

### 3.2 失效与刷新

- 接口删除/重建、MTU/路由改变、配置 revision、lane 换代和发送 `EMSGSIZE` 等相关错误使旧快照失效。Linux 优先复用一个设备级 netlink 监听器；没有现成机制时只做最小 route/link 事件订阅，不每 lane 启一线程。
- 事件合并为有界刷新请求；最多一个同 scope 的刷新在途，风暴时合并，不让每包失败再次做查询。可用设备级低频兜底观测（初始 1s，作为工程起点），不增加新的用户配置项；若平台无法监听，明确说明兜底延迟和失效行为。
- 更新投递到 owner，在批次边界生效；开始下一次提交前核 revision。降低预算后不再提交超过新预算的排队包。未发送明文交原分片/超限处置；已固定密文不重新 seal 或改 seq/PN，可按原规则放弃并计数。不能为了修缓存同时完成整套新分片。
- 保留外层 DF/内核拒绝超限的保护。路由改变与实际发送存在竞态，不能声称每包实时查询就能消除；监听/错误反馈关闭失效窗口，真实 MTU 降低测试必须验证不产生外层 IP 碎片、不继续错误发送。无法安全判定时暂停受影响 lane 的提交并刷新，其他 lane/方向继续，不能持全局锁等查询。
- 变化后的扩大也要依据新观测和所有约束，不能直接恢复旧最大值。事件丢失、监听重连、接口编号复用的处理要有 generation/revision 反例。

Windows 复用原接口通知/控制层网络变更入口，公共数据结构不写死 Linux FD；本任务不凭 Linux PASS 宣称 Windows native 行为通过。平台未实现的适配明确 NOT_RUN，但不得引入编译/API 回归。

## 4. 批次 B：落实方向所有权、批量 I/O 和复用

### 4.1 移除数据包对全局 registry 的依赖

准备/安装时从 registry 取稳定 lifetime handle，启动时将 TX/RX 可变状态分别交给自己的 worker。共享只读配置通过固定生命周期引用；跨方向通知使用已有有界队列。不能让 RX/TX 共持一个内部可变 owner mutex，也不能新造一套 crypto/PN/arena 状态绕开原 owner。

现有 `ProtectedScopedOwner` / `EarlyRxBoundaryOwner` 若绑定双向状态，做最小方向拆分：保持外部可信 admission 入口和事务，Prepared 时不能运行业务；双方向安装确认后 Active。失败时只撤销候选，Stop 先停止接入、通知两端、待 lease 归还后再释放。registry 不在设备读取、AEAD、route 刷新、TUN 写入、raw 提交或 join 等待期间持锁。单线程独占资源上的重复 mutex 可在所有权验证后消除，不能用裸指针或提前 free 换性能。

### 4.2 ready-only 批处理

复用现有 M1/M4 的有界 batch 与发送结果契约。先等一次 ready，然后非阻塞 drain 已就绪数据，最多32包/约100µs工作片段，之后重新服务其他工作；不为了凑32包等待，不为减少 syscall 增加低负载延迟。TUN 仍是逐 packet read/write，可一次唤醒 drain 多包，不伪称 TUN 支持 recvmmsg。

原 raw 后端接实际适用的 recvmmsg/sendmmsg，避免为本任务强制另换 AF_PACKET 或整套网络后端。处理 prefix/未发送 suffix/uncertain，保持同密文重传、PN/seq 不重复消费；EAGAIN 不忙等，不丢尾部，不按一次 syscall 成功推定全批成功。已有一次1包路径可用于稀疏自然退化，不另保留第二套业务实现。

原 MTU≤正常预算的包仍即时进入发送；预算到期/Stop/控制的机会不能被持续 RX 抢完。分片/FEC 仍沿现有边界，不引入新计算屏障。

### 4.3 存储和观测

worker 启动时预分配 RX/TX batch、header/iovec/scratch，循环 clear/recycle，复用现有 slab 和 immutable record。去掉已发现的每轮 Vec 分配；记录 freeze/Arc 等其他剩余分配，不把“包体复用”写成整个热路径零分配，不因此重写全部内存池。

普通计数 owner-local 累加，低频快照；线程 CPU 在测量边界采样，必要的状态发布最多低频执行。普通性能关闭逐包日志、trace、strace/perf。不能通过停止业务完整性校验、改变抽样比例或隐藏线程成本获得更好结果。

## 5. 批次 C：功能回归（一次构建，批量验证）

沿既有 qualification manifest 关联用例与来源，不新造测试账本。重复运行已有同义用例没有价值；下面是本改动必须覆盖的风险：

| 组 | 必要反例与实际观察 |
|---|---|
| MTU缓存 | 初始化不可信参数拒绝；稳定流量查询次数不随包数线性增长；真实 namespace 中 MTU 降低/恢复、route/ifindex 换代、EMSGSIZE、事件合并；旧 revision 不能授权超限发送 |
| 生命周期 | 停止时仍持 batch/driver loan，延迟归还后才释放；重连/rotation 旧 generation 不能交付新 scope；关闭期间刷新回调不会复活 owner；B01–B04已验部分不退化，未验部分仍 OPEN |
| 批量 | 0/1/32/33 ready、部分发送、EAGAIN、uncertain、短/坏包、队列满；单包无需等 batch；存储按代回收，旧借用不提前 free |
| 交付 | 原三 cipher 功能回归、payload/PN/去重；指定 DATA 缺失后后包仍首到；持续一方向不饿死另一方向与 Stop；MTU内最大包与超限处置保持 |
| 系统 | 引擎/原Go桥接/ABI必要 native 回归；现有跨平台编译门；未知平台行为记 NOT_RUN/UNSUPPORTED |

计数使用测试适配器或诊断构建，不给正常包增加原子统计和全量追踪。Linux真实 MTU变化至少一个实际内核例，不用全 mock 宣称通过。其他竞态优先 fake clock/确定性交错，不用真实长 sleep 凑覆盖。

## 6. 开发后的同 Actions A/B 契约

### 6.1 固定比较对象，直接复用夹具

本轮主比较为**优化前 Rust A vs 优化后 Rust B**，不是再用旧 Go 两端对新版单 owner 算比例。A 从 `333c1b3f7af6e9a717ba4a6b78bf6a378899f3d5` 固定；若开始前已有相关修复，先说明差异并固定新的、没有本轮优化的 A。不得使用浮动 main/latest。

复用 `m0-old-new-paired-diagnostic.yml` 的同 job/顺序/产物核验设计，以及 `bridge_v4_embedded_perf_linux_test.go`、`run-v4-tun-netns.sh` 的真实业务拓扑；只补 Rust/Rust 两产物消费和必要计量。不得继续把旧 Go→新 Rust的拓扑差异当主要对照，也不为等完整产品推迟本轮。

共同 harness SOURCE、配置、seed、负载/验证 schema、namespace/loopback或veth拓扑、cipher、toolchain、Release/features、CPU计量边界必须一致。保留现有单 namespace Go peer + Rust owner 路径可作为首轮有效**开发路径优化对比**，但不宣传完整产品/两端 Rust/物理资格。共同 Go 发生器和收包校验成本仍包含在总进程指标中；Rust线程细分只是子集，两者不相加。

若要修计量，例如去掉逐轮 CPU clock 改边界采样，先把**同一 measurement-only 补丁**应用于 A 派生源码和 B，固定各自 SOURCE、补丁/夹具 hash 并审 diff；该补丁不能顺便缓存 MTU、拆锁、改 batch/负载。原 A 历史观测保留，不用不等价时钟冒充产品收益。若暂时只能公平测整个进程，先报告总进程 CPU，细分标 NOT_MEASURED，不创造不可比线程比例。

两个候选在 Actions 预编译，记录来源/依赖/toolchain/flags/features/文件 hash；消费者只验证和执行，不现场编译。一个性能 Action 一个场景/配置/seed、一个测量 job，A/B在该 job同VM串行。冷启动/建连/下载/压缩不在计时内；每leg清理本轮 owned namespace/进程/队列、重建相同拓扑。不同 run 的 CPU-s 不直接相减。

### 6.2 有限测试集合与顺序

| ID | 场景 | 时间与用途 |
|---|---|---|
| P10-AB | Normal1/FECoff/ChaCha、无人工丢包/延迟、UDP应用净荷64/256/1200等包数，双向各10Mbps，seed631；A→B | 每leg热身10s+测60s+排空3s；主要 CPU/交付/p99结果 |
| P10-BA | 与上行完全相同配置和seed，B→A，另一个独立Action | 同样时长，检查顺序和宿主波动；分别报告配对比例，不混跨VM绝对CPU |
| SPARSE-AB | 同原路径、无人工损伤、双向各20包/s、64/256B等包数；A→B | 热身5s+测30s；确认不等batch、无固定延迟台阶、idle/Stop可响应；不比较小样本百分比节省 |
| D10-AB | P10固定配置，诊断ON，A→B | 各10–20s、单独Action；有界syscall/内部慢路径计数定位，不用于正式CPU/p99优劣 |
| C50-AB（条件项） | P10包型，双向各50Mbps，A→B | P10注入有效、无容量证据才跑一条；A若已容量受限，降低到共同可测点或报告容量差异，不能把少交付当省CPU。不要接着机械跑100/200/500 |

功能回归可同一次功能 Action 合并多场景；上表性能行必须分开，每行仅该配置。已有自动触发 workflow 要按依赖选择，避免每个证据/H提交再次启动70s业务。构建产物跨上述run复用，精确核hash；不要求每个内部重构点重跑整个集合。P10-AB先排除明显失败后再做其余项。并行worker Action各用独立VM，不与本job测量争抢同一VM。

D10诊断优先 `strace -f -c` 的有界汇总和必要的目标文件路径摘要，或等价可用方式；明确追踪的是整个混合进程还是Rust线程。区分夹具正常socket、路由查询socket和steady send/recv，不能把所有open/socket都算产品问题。只保留摘要、计数与hash，不持久大pcap/逐包日志。统计手段不可用则用确定性调用计数+代码路径证明，诊断开销不能污染普通测量。

### 6.3 必须输出的数据

- 每leg actual SOURCE/build manifest/hash/target/flags/工作负载hash、同job身份与单调起止时间；注入器实际速率、发送/首到/缺失/重复/非法包和drain后统计。
- 进程 user/system CPU-s、CPU-s/GiB实际交付、CPU-s/Mpacket；所有产品/辅助线程包含在总量，RX/TX/control/route watcher分项注明是否完整。不把跨两端、单端或注入器包含范围不同的数字算收益。
- p50/p95/p99业务到达年龄、样本数、10ms首次交付桶与有offered时最大连续空洞、队列年龄/高水位、RSS和退出资源。loopback同host单向年龄不是公网RTT；新加独立RTT探针时双方一致，不抹掉missing/late。
- 实际 CPU型号/ISA、逻辑核/配额可用性、PSI/steal/背景负载，内核/socket/driver drops；不可读写UNAVAILABLE，不当0。最大吞吐未测不得从10Mbps满速推断。
- 查询/刷新次数及原因、查询socket生命周期、read/sysfs/syscall/包、实际batch大小分布和分配热点。可用诊断构建收集，普通样本只留低成本必要统计。

### 6.4 判断方法：不靠刷数字收尾

正确性硬门继续严格：损坏/重复交付、跨账号/generation、错误密文重传、提前释放、超限错误发送不得出现。健康无损P10应全量交付；少量missing先查注入/内核/程序证据，不因平均速率接近10M就抹掉，也不凭单次宿主drop断言协议失败。实际注入平均目标初始允许±2%，偏离需解释/分类，不能降低注入让CPU更好看。

结构验收：稳定配置期间 route/接口观测随初始化、变化、低频兜底增长，不随业务包数线性增长；数据工作不持global registry锁；预分配batch实际复用；ready批量不会等待凑数；普通路径没有逐包诊断syscall。保留无法消除的实际成本并说明，不宣称整个热路径零分配/零锁。

CPU主看每个同VM配对的 delivered-normalized user+system成本，子项解释原因。约10%以上且AB/BA一致的降低可视为有意义的初始信号，**不是必须省10%才能结束的硬门**；小差异/顺序矛盾记INCONCLUSIVE，不能报告“已经省4%”。若机制修复成立且无性能回归，但收益低于噪声，可按“结构修复完成、CPU收益未定”收口，保留实测结果，不强行继续重写。

p99与首到优先。初始调查触发带为B相对A增加超过 `max(0.2ms, A的15%)`；这是同host低延迟实验的定位参考，不是新的全产品SLA。必须同时看missing、连续空洞、队列和宿主噪声。可重复的新增凑批延迟/方向饥饿/长停顿必须修，不能用CPU下降交换。单次尾部异常允许一次有理由的复核，不无限加seed或放宽阈值。宿主/注入器容量不足停止更重工况；产品owner饱和则报告产品瓶颈，不一概甩给runner。

## 7. 完成、停止和恢复后续工作

完成条件：批次A/B已落在实际调用链，批次C必要回归通过；P10-AB/BA、SPARSE与D10按实际能力完成并留痕，C50按条件执行或明确因容量跳过；指标可解释、无未处理的可重复退化。CPU收益可为已确认或INCONCLUSIVE，硬门失败不能标完成。若外部条件阻断必要验证，明确BLOCKED边界，不把未跑当通过。

沿原 `docs/devlog/M0/`、`docs/evidence/M0/`、qualification manifest、cursor留痕。解释旧新实际路径、变化成本、每项PASS/FAIL/NOT_RUN、残留问题与回退。内部优化不新增CLI/GUI配置，在日志注明“无新增用户参数”；默认行为和原能力目录不改。

本任务关闭前保持原023产品 `unverified=true`、默认production features0和物理NOT_RUN。关闭后 M0 再更新 registry 分配，恢复原 R1 超MTU自动分片/重组、必要M1/M4集成和023剩余B01–B04，再按R2–R6推进；不要把功能集成或治理自测当成新的性能对比。已完成任务不因新agent接手重跑，发现真实新反例才重开。
