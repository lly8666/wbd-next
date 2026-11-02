# PLAN027A｜统一V4 MTU与超限包处理

用户2026-11-02指定次序：**PLAN027收口 → PLAN027A → PLAN028 → 029/030依接口并行**。本提交是完整施工方案，不修改正在执行的产品/测试，不抢占M0 cursor。027正式收口后M0按既有registry登记此包即可连续推进；不必重新发明审批。若027尚有MTU阻断，可先摘取本包最小根因修复并记录，027A扣除同源已验内容，不能循环互相等完成。

开工：[M0-PLAN027A](../prompts/M0-PLAN027A.md)。唯一规范：[MTU_CONTRACT](../architecture/MTU_CONTRACT.md)。下游028会话/config、029 padding消费它，不再重算。

用户输入口径已确认：**MTU设置为外层完整IP上限，默认1500，不含L2；内层自动计算且只读展示。**现有Windows `--mtu`/Linux `--outer-mtu`不改单位，归同一意图字段；不得把内层手动override作为常规配置保留下游。实施/导入/UI细则见契约第1节。

## 1. 审阅结论与实证缺口

附件按H915 `1d220ec1`审阅，本包又核到main H916 `9947ac4a`（开工刷新）：

| 已确认代码事实 | 位置 | 要改/不误判 |
|---|---|---|
| record基础31，FEC2 source10/repair12+符号2，Game16 | `crates/wbd-codec/src/record_frame.rs`、`fec_v2.rs`、`lib.rs` | 附件主要字节表正确，不能把FEC14说成每个source固定头 |
| `FrameBudget` GameFEC预期1399，真实GameFecTx另扣type1 | `path_budget.rs`、`path_budget_tests.rs`；`crates/wbd-engine/src/v4_game_fec.rs` | **应1398**；运行端已有更紧保护，不宣称线上必已越界 |
| Go独立公式/额外gameFecBudget，Windows `min(tun+reserve,1400)` | `r0/go_overlay/internal/v4productcli/linux.go`；`cmd/wbd-client/m0_native_v4_windows.go` | 归口纯Rust预算+冷ABI；显式限制原因，不能只修测试数字 |
| 部分Windows `path_mtu`仍注释为Wintun读回却用于outer预算 | `v4_windows_owner.rs`、`bridge_v4_windows_wintun_lease.go`及真实native caller | 逐条追**当前实际调用**；H799 Game外层传值已修不能重复推翻，Normal/FEC等仍需量纲核对 |
| MSS模型只min(mss,本地容量) | `path_budget.rs` | 对端较小MSS+DATA options的额外扣减需按原始MSS语义核对，不能重复扣已adjusted输入 |
| Linux配置576..9000，实际Game/Windows含2048等约束，Linuxfq helper还验1280..1500 | `linux.go`、`v4_game_public_kernel.rs`、Windows native runtimes | 模型可算≠产品可用；改公开能力与校验，不盲扩大所有buffer |
| Linux Normal有LINK慢路径；Fixed不授权裸Normal LINK；WindowsNormal RX只交Ordinary | `v4_embedded_go.rs`、`v4_windows_owner.rs` | 不假装LINK全模式接通；保留现有兼容，统一IP层超限语义 |

附加修订：外层路径值只是已知上限，不自动证明PMTU；计算与OS应用分离；TX/RX及lane方向分离；控制包表不能复活线上M2；不把所有oversize转成fatal/Stop。原审计若和新证据冲突，按实际encoder/调用链修正本表，并留理由，不维护两份权威。

## 2. 连续施工顺序

### A. 预算与调用方一批打通

1. 在现有path_budget归口V4 typed层次/模式、31/14/16/type1、MSS/options、真实buffer cap，修1B及旧V1误选。复用codec公开常量，不造第二份常数库。完整record vs body、IP vs L2、inner vs outer在ABI字段注释与类型上分清。
2. 导出纯冷ABI可pre-TLS derive，Go初始MSS/record offer、认证后OS计划、Rust owner/fec/game、M4最终packet使用同一输出。移除公有V4重复加减helpers，不把仍需codec边界验证删掉。pack ABI manifest配套，不能旧Go配新DLL静默布局错位。
3. 每方向/lane冻结budget revision，现有单owner更新；Win真正绑定outer物理出口预算与inner Wintun读回，不能拿一个值上下替用；Linux初始TUN过早放行/单lane只降不更新的行为按规范统一。
4. 清掉隐藏1400/1280上限，或若实有限制则明确actual limiting reason/适用模式，不能以“统一”掩盖未利用空间。公开外层≤1500先收口；旧9000显式实验/unsupported，不为了保留CLI范围扩大全部热buffer。老键单位和配置迁移提示写清楚。

### B. 一份超限分类与慢路径

先复用内核MTU/MSS/PMTU与成熟工具。正确TUN先挡大多数异常；本轮必须落实DF反馈、合法DF0 IP碎片通过、单包错误不杀会话。若入口确需用户态IPv4碎片，做**一个**共享有界慢路径，复用现有32片轮次调度/小包优先/owned buffers；不新增全模式LINK，不改FEC math/wire，不追高损大UDP零丢。

Normal已有LINK原文/乱序/有界回收继续可用；Windows/FEC/Game不能伪装支持。禁止既先IP分片又为同一层无谓LINK分片；仅当实际每片仍超过不同载体预算且已协商支持时才有必要的下层处理。应用64KiB TCP write与IP大包区别写进夹具摘要。

### C. 路径变化、组合和清理

复用027已通过的lane/generation/Stop机制，处理budget收窄、旧parity/冻结repair退休、健康Game lane保留；不另开生命周期重构。正常MTU变化能安全在线更新则更新，否则明确重建，不能永久busy或静默持续掉包。更新CLI/config/帮助、已适用GUI说明和功能卡；029后续新UI只接同字段。

代码/双方接线/配置/夹具先完整写齐，再冻结SOURCE构建一次。小范围编码unit可先诊断，不每helper开全产品Actions。预算纯函数与测试向量可并行准备，Windows/Linux adapter在冻结接口后可分工；共享ABI/owner/MTU规则一位作者，M0串行集成。单M0等Actions时推进其他独立检查，不新建工位/治理平台。

## 3. 可复用Actions：有限集合，不全排列

复用现有原Go真实TLS + Rust owner + 真Wintun/Npcap/Raw/TUN夹具、M0精准SOURCE构建/manifest及最近MTU样本；不搭第二套数据通道。参数至少 outer MTU两端、mode/FEC、peer MSS/record限额、TCP options、padding、负载包型/DF、丢包/延迟、MTU变更/rotation时点。双方管理连接与业务分离，仅对owned业务网络注入。

**每Action一场景/测量job**；一个场景允许预声明的阶段波形/边界包族/顺序同VM A/B，双端是必要进程。不同模式/平台Action独立并行；单测功能可批量。先完整一套字节tests再原生小矩阵，不重复20种rate×每个MTU×全部模式。

| 层 | 具体覆盖 | 合格条件 |
|---|---|---|
| 纯模型/实际codec | 1500/1492/1400/1280、最小可用/不可用、peer MSS536/1200/1460、TCP20/32/60和IP options、caps较小、三AEAD、源/最大repair/partial、Game、合法LINK、padding | 手工独立literal golden与**真实编码→seal→IP packet**一致；1500 GameFEC1398合法/1399不能单record；不从被测函数自生成expected |
| 协商/OS/能力 | 两端同MTU与1500:1280、较小peer cap、Go offer/MSS/owner/OS读回、所有7模式 | Normal off/fixed最高/auto、Game2/4 off/最高；已知实际限制一致，数据放行前applied；不能单靠日志数字相等 |
| 真原生边界 | 7模式Windows↔Linux逐项60–90s、5–10M Normal/3M Game，模式cap−1/= /+1；一端1280的代表组合 | 合法业务无损完整、超限按DF/能力处理，后一小包与其他流继续、Stop成功，外层DF无超P；损伤设0以隔离尺寸错误 |
| 应用大包 | 持续TCP 64KiB write+小UDP；UDP小包/边界/1728/4096/65507应用payload，DF on/off分清；IP options及已分片输入做低成本组件用例 | 内核分段/碎片实际发生且能重组，DF正确拒绝/ICMP/EMSGSIZE；高PPS不先与jumbo压力叠加；故意raw注入单独记，不冒充普通应用 |
| LINK既有兼容 | Linux Normal/off已支持路径1728、跨32片、最大合法65535内层IP；一片丢失/乱序/重复，旁路小流 | 全片无损完整、缺片有界过期、不HOL、不混generation；不把组件重组PASS声明Windows已接通 |
| 动态组合 | 1500→1280→恢复、peer cap收窄、新lane容量不同、Auto切档、旧repair/parity在途 | 新包不越界，已冻结repair不改密文；无无限等待，受影响owner可有说明的有界重建。选Normal和Game4/FEC代表，不重刷027全部黑洞矩阵 |
| 保护性能 | Normal off与Game4最高各一容量内代表，新旧同VM顺序，普通近cap包+小UDP；初始外层参数相同另报实际包型/新增PPS | 分端CPU-s/百万交付包、CPU-s/GiB、RSS、offered/first/missing、p99与最长全流空洞；不靠换包型/扩大实际业务包误称算法收益 |

Linux ARM64原生完成预算ABI/codec和Normal+GameFEC边界代表；Windows amd64实际新DLL加载与两端包尺寸必须测，编译成功不是运行。相同驱动路径无变化可按diff引用未变部分精确旧资格，修预算后的关键界值必须新SOURCE实测。

选项测试不扩生产能力：当前outer IPv4 builder若只支持20B，外层IP options只验数学与明确拒绝；真正wire组合验已支持的TCP options。内层合法IPv4 options/碎片沿现有IP解析或成熟分片helper，不能拿不支持外层options为由丢合法内层IP。

弱网只补两条高价值组合：Normal最高FEC、Game4最高FEC，10M/逻辑3M，单程250ms、5%→30%→5%预声明波形，各120s；混合近MTU大小UDP和TCP。先算每IP片/FEC符号/副本的实际损伤与完整datagram概率，30%不设大UDP零丢或1s固定恢复门。主旨是无额外全局HOL、恢复/清理有界、当前数据不越界；性能疑点最多一次必要反序，不刷seed。宿主容量先报到点停止更重同族，不要求重跑027的200/500M全部项目。

若附件说“跨32片/65KB都要过”，须区分supported LINK、内核IPv4碎片与未支持模式；不能靠下调真实TUN MTU后应用已经拒绝，写成“大包成功通过”。反之合法OS的EMSGSIZE是正确DF结果，不当作产品坏包。

普通原生夹具只输入外层MTU，让真实产品自动应用内层；不可另注入预先算好的TUN值帮助产品过关。明确标出的异常/兼容测试才可强制虚拟MTU。补配置保存/加载/CLI别名/UI只读生效值用例：配置外层1500经过模式切换或路径收窄仍保存1500，内层随实际预算更新，server无需手填同一内层值。

## 4. 宽而明确的门与退出

- 不可妥协：实际IP≤生效P、实际record≤W、内容/认证/generation正确、无截断/重复首到/全局Stop误触发、合法DF反馈、supported范围无损完整、owned回收。
- 经验门：first/p99/CPU先看同源无损/同VM父版，缺失单列；普通热路径不应新增syscall/FFI/逐包分配。容量内CPU持续约>5%或p99异常增加先定向查原因（诊断触发线，非跨VM机械FAIL），最多一条反序；正常噪声不阻塞收口。
- 优先复用有效等价证据，按实际调用差异裁剪；没有新异常不扩测。预算与大包正确性完成后返回整体计划，不把此包变成PMTUD/IPv6/jumbo/调度架构重写。
- 退出必须同时有规范、唯一计算入口/调用清单、配置读回、跨端界值、超限处置、受影响性能保护及功能卡证据。主线current task改为027A时用现有registry/cursor，不修改旧失败为通过；完成后接028，028不再重做预算。
