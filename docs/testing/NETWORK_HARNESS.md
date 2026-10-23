# 可复用真实网络 Actions 夹具

**2026-10-23新外层策略**：新SOURCE请求显式 `policy=outer-single-repair-v2`；双端必须回读同名policy、`repair_attempt_limit=1`、固定shadow逻辑上限和retain硬帽。IID外层一次修复理想残余为p²、repair/fresh≈p；Normal/off 1/2/5%新稳态参考分别≤0.15/0.25/0.75%。旧请求未声明policy时仍按历史证据解释，绝不用新门槛重标旧PASS/FAIL。详见[一次修复决策](../decisions/NETWORK-ONE-REPAIR-20261023.md)。

2026-10-21 用户直接授权实现。入口：`.github/workflows/network-harness.yml`；请求格式示例 `tests/network/request.json`；预置工况 `tests/network/scenarios.json`。实现只增加测试工具，不修改产品、M0 工作游标、权限或生产开关。接入正式客户端/服务端 `wbd-v4-client/server`，复用成熟 Go TLS 和真实 Rust raw/TUN owner；**不借测试 helper 伪造数据路径、认证、ACK 或应用交付**。

这落实 `docs/architecture/TEST_PLAN.md` 的持续业务、产物复用、单场景 Actions 和理论允许带原则，不替代它。已有小回显夹具继续作为便宜的功能回归。

## 开始一次实验

1. 使用已有 `m0-plan012-combined-functional` 构建产物，填 `bundles.A` 的完整产品 SOURCE、build run、attempt、artifact ID 和下载 ZIP SHA256。不要用当前文档 HEAD 冒充编译 SOURCE。示例产物会过期；过期时需要真正重新构建，不能只改编号/hash。
2. 复制 `tests/network/request.json`，或用 `python3 -m tools.network_harness.request off-iid5-rtt50 --output tests/network/off5.json` 展开一个预置工况。这是生成配置，不是本地执行测试。检查产物、速率、损伤、允许带并提交文件。
3. GitHub Actions → **Public V4 network scenario** → Run workflow，选择包含夹具/请求的分支，`request=tests/network/off5.json`。请求必须是该提交中存在的 JSON，不接受任意脚本或 shell 参数。
4. 看 job summary 和 `network-<run>-<attempt>` artifact：`result.json`、每 leg `summary.md`、`client/server-traffic.json`、网络快照、损伤变更时刻、进程/宿主采样、产品计数。
5. 在现有角色 devlog/evidence/cursor 记录本次 run/attempt、精确二进制 SOURCE、夹具 SOURCE、结果和限制；不要另建交接系统。没有产品变化或新故障假设，不重复已完成工况。

**一个 performance Action 只有一个测量 job、一条预声明工况/seed。** 三阶段损伤波形属于同一场景；没有跨配置矩阵并发。`bundles.B` 加入另一完整产物后，设置 `order=AB` 或 `BA`，两份产物在同 job 顺序运行，前一 leg 停止、销毁独立 namespace 后重建。需要反向顺序时另开一条 BA Action；不能把两台 VM 的 CPU 百分比直接对比。不能在本夹具测量 job 重新编译产品。

## 已实现的能力和边界

| 能力 | 真实行为 |
|---|---|
| 持续发送 | 两方向独立进程，收发循环持续推进，不等上一包 ACK/回显才发下一包；有界批次保证收发公平 |
| 业务 | UDP、真实多连接 TCP、按字节份额混合；独立双向并发 RTT 探针；小包/大包按配置权重循环 |
| 计数 | `sizes` 是应用 payload 字节，包含夹具序号/时间/完整性头；Mbps 是应用字节率。UDP 的内层 IPv4 长度再加 28B；TCP write 不是线上一个 IP 包，真实内核负责分段 |
| 阶段 | 预声明 1..16 个阶段，总测量≤1200s；热身默认10s、尾部 drain 5s；各阶段双向损伤和负载比例独立 |
| 损伤 | 每方向 delay/jitter、IID loss、netem Gilbert-Elliott、duplicate/reorder、速率限制，实际 `tc -s -j` 回读；Ubuntu24.04实测tc不支持seed，默认明确记 `netem_rng=unseeded_recorded`，seed只固定业务正文。请求seeded时必须系统支持，不悄悄回退 |
| Game | 真实 Game2/4 CLI；独立 lane netem 队列/seed 或一个共享出口队列；可按 lane 端口阻断一条/全部，保留规则命中数 |
| 相关性 | **共享 netem 随机队列不等于完美相关丢包**。相关黑洞用同一阶段阻断所有 lane；GE 以包转移概率定义，不能说它天然等于固定毫秒突发 |
| MTU | 回读实际 TUN MTU；默认拒绝超 MTU UDP 负载计划，防止误把发送失败当线路损失；显式 `allow_fragmentation=true` 才测大 UDP 的真实 IPv4 分片兼容性 |
| 队列 | netem 默认32768包并公开实际 backlog/drop；这是模拟延迟所需队列，不修改产品 socket buffer。高 PPS×延迟要先计算队列容量，队列 overflow 不能冒充预定 IID 丢包 |
| 数据完整性 | 带方向进程上下文、连续序号、发送时刻、阶段、长度及确定性高熵正文；完整正文比较；首到/重复/乱序分开。原始正文不持久化 |
| 时间 | 同一 Linux kernel 的 monotonic_ns 可跨 namespace 直接计算单程；RTT 探针单列，绝不把单程当 RTT。不能将这条保证移植为物理跨机单程时钟保证 |
| 可观测性 | 1s 宿主/产品/注入器 CPU与RSS、CPU PSI/steal、内核/CPU型号/flags/quota；阶段 socket、接口、qdisc、UDP error、TCP状态计数；10ms发送/首到桶 |
| 来源和清理 | ZIP/manifest/各文件 hash、平台、SOURCE、run/attempt 校验；仅本次 namespace/进程/临时证书；限量日志；无持续 pcap；结果不上传二进制/私钥 |

夹具自身在 `network-harness-check.yml` 做配置/模型/完整性/延迟桶/计数反例和真实本地 TCP+UDP 双向测试；这是**夹具测试，不是产品 PASS**。网络实验用的是正式 V4 公共入口，路径当前仍受构建 feature 控制，不自动取得生产启用资格。

## 不支持的产品能力必须诚实显示

当前已接线 CLI 支持 `normal`（FEC off）、`fec-fixed`、`fec-auto`、`game2`、`game4`。固定档 `fec_profile=0..6`；auto 的启动档由产品控制，不能靠传一个未使用参数声称换了启动档。固定/自动档必须从双端真正 applied 回执验证 requested=applied、pending=false；固定档还要匹配 profile。

**当前 Game CLI 明确设置 FEC off。** 夹具不能将它标为 Game+FEC strong，也不能把 profile 参数被忽略当作档位生效。请求 Game FEC-on、cipher选择、重传开关/比例会明确拒绝为 UNSUPPORTED，直到产品暴露真实参数和 readback。不要为跑测试修改这条实际语义，更不能偷偷回到旧 Go 数据面。

现有产品日志有 Normal/M2 首发、认证 ACK、修复次数、uncertain、blocked，以及 Game copied/delivered/raw_received/auth_rejected。**没有**足够公开数据观测修复字节预算、有效/多余重传、逐包修复延迟、FEC实际k/r/等待年龄、实时自动档曲线、owner锁等待等。结果相应填 NOT_OBSERVED；最终 applied 不证明中间升降曲线。M0 后续可以让产品按低频 JSON 暴露这些现有计数，再补一个解析器；本夹具不反向调用测试 ABI 或另造一套自适应控制器。

不支持的后续工况：Windows原生、ARM本机、真实外网、DNS互备/路由/UI、换代/休眠控制、cipher/repair运行时切换、外观抓包、DF超限拒绝的专门功能资格。这些继续用已有产品生命周期/物理夹具。本夹具的 `rate_scale=0` **仍有 RTT 探针**，不能冒充无真实 payload 的 idle 验收；黑洞恢复也不自动等于 lane重建功能通过。

## 结果判断，不刷零丢包

默认弱网工况只要求注入有效、路径/模式/清理正确、完整性正确、持续业务有真实交付，并记录损失/延迟；不强制 off 在5%/20%丢包下零业务丢失。lossless 示例允许0.1%业务损失，门槛是公开的开发允许带，不能悄悄改成产品最终 SLA。

- `PASS_SCOPED_OBSERVATION`：本场景已完整观测且满足声明门槛，不等于所有功能或性能验收完成。
- `FAIL`：产品业务/完整性/Stop/配置回执/明确允许带失败。保留失败，不由 aggregate 换成通过。
- `INCONCLUSIVE`：注入不足、夹具丢包、阶段时刻偏差等使本次实验结论不能成立。单次宿主PSI峰值单列警告，不自动否定已经真实完成的业务；持续争用令 `performance_comparison=INCONCLUSIVE_HOST_CONTENTION`，不凭一个CPU/PSI数字宣布容量不足。
- `UNSUPPORTED` / `INVALID_REQUEST`：当前真实入口不支持或请求错误，不能填产品 PASS。

UDP实际发送率默认允许±3%偏差，不以一个 skipped slot 判无效；TCP由于自身拥塞控制出现发送反压要单列 `TCP_BACKPRESSURED`，不直接归咎生成器。未交付通过 `missing_after_drain` 报告，超 deadline 包加未交付包一起统计。p99仅是已到包分布，不能丢掉慢/未到包后宣布低延迟成功。大 UDP 丢一个碎片即可丢整报文，不能与小包同用固定零损门。

`cohort_delivered_app_mbps` 按发送阶段归属，包含 drain 内迟到交付，**不是阶段内即时 goodput**；`arrival_window_app_mbps` 和10ms首到字节桶另报实际时段交付，不能用drain掩盖阶段停顿。总进程CPU（处理双向）按本进程收到业务归一化 CPU-s/GiB 和 CPU-s/Mrecords，并公开分母；需与交付数量、发送比例一同对比。接口外层字节含控制/修复/冗余，但不能把总包数除首发包数当“重传字节超过10%”。稀疏业务还另有比例豁免。

理论参考只解释，不充当万能门槛：新 `outer-single-repair-v2` 下IID理想残余为p²、期望repair/fresh≈p；p=5%时分别0.25%、5%。旧两次策略的p³/p+p²仅用于历史SOURCE解释。系统性RS实际(k,r)的单源残余为 `p*P[Bin(k+r-1,p)>=r]`，不是简单“丢包低于r/(k+r)就全恢复”。真实模型还要代入短块分布、及时发送的parity、相关性、多lane共享编码结构。Game独立复制和同时黑洞分别测，不拿p⁴解释相关黑洞。实际修复时序未观测时不能宣称已达到模型。

## 有限测试顺序与容量停止

后续按 [包长与极限容量补充](NETWORK_CAPACITY_ENVELOPE.md) 选择少量代表点，覆盖同维度后可跳过中间档。prepare生成 `capacity-envelope.json`（UDP份额、FEC满组/单源组与netem队列估算），不在测量循环计算、不自动改队列或PASS门。TCP分段和分片另需真实统计。模型可单独用 `python3 -m tools.network_harness.envelope --request tests/network/request.json` 读取。

1. 先跑示例 Normal/off、10Mbps/方向、lossless，确认生成器和实际产品有容量。需要业务混合，再跑相同速率真实多连接TCP+UDP。
2. off 的1%、5%与双向非对称；RTT50/150/600ms，优先实际常用点。高损20%只要求新包不被修复拖死和预算可解释，别强求零丢包。
3. 固定档以实际支持档位覆盖，选常用strong和低档弱网代表；auto跑低→高→低及上下行不对称，实时档位遥测未接入时保留曲线未验。
4. Game2/4逻辑3Mbps，独立随机损伤与共享黑洞分开。Game+FEC等产品接线后再扩，不假跑。
5. 同一源码再做MTU内边界、IPv4大UDP分片、TCP大write、突发发送和限速恢复；延迟/丢包幅度按目标模型解释，不穷举全部笛卡尔积。
6. 有余量才10→50→100→200→500Mbps，每个点一个独立 Action。小包PPS另列，FEC/Game先算外层膨胀。发现注入器/宿主/内核容量不足就停止更重工况，写 PROJECTED_NOT_TESTED 与依据。产品单核/锁饱和仍是 DATAPLANE_BOTTLENECK 候选，不能以总CPU未到100%掩盖。

同VM AB不能消除随时间变化的宿主争用；两leg都要有效且业务交付/冗余语义一致才能比较。当前报告保留成本原数，不自动宣布“优化X%”：由agent先核观测边界、背景PSI、丢包和队列，再给结论。如果数据不足，只补能区分原因的一项观测，别重新跑整套。

`unseeded_recorded` 的损伤是同分布统计比较，**不是同一逐包丢包轨迹**；即使不同环境都支持seed，产品改变发包顺序/速率也会改变哪包被丢。比较结论必须看实测损伤计数/流量，不能把相同请求seed称逐包精确重放。确定性黑洞的时间表和规则另行记录。

## 已执行范围（2026-10-22）

夹具 `38c7e2f` 的8项自检及真实内核选项检查已通过。固定产品 `bdcd66c` 的双向10Mbps lossless UDP大小包通过；同产品1% loss / 50ms RTT的UDP+TCP混合场景真实完成但为INCONCLUSIVE：TCP反压使请求的5Mbps/TCP未达到，尾延迟也需继续定位。不是全矩阵PASS，也不是Windows或物理机资格。

精确run、计数、失败解释与artifact hash见 [验收开发日志](../devlog/network-harness-20261021.md) 和 [结构化证据目录](../evidence/network-harness-20261021/)。接班优先复用已暴露的混合业务问题，不无目的追加更高负载。
