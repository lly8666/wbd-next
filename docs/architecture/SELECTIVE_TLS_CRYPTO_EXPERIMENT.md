# Normal/OFF：TLS 密文复用实验架构

状态：**LAB_ONLY_COMPONENT_S0_PASS / IDEAL_ORACLE_S1_MEASURED / NEGATIVE_APPEARANCE_LAB_CAPTURED**。真实 Go→Rust→raw/TUN 接线、生产 Stop/generation/MTU、业务 p99 和端到端 CPU 仍 NOT_RUN；精确 SOURCE/Actions/最终否定结论见 [本岗位状态](../evidence/selective-crypto-work/status.json) 和 [最终实验报告](../evidence/selective-crypto-work/FINAL_REPORT.md)。本页只在 `experiment/selective-tls-crypto` 生效，不改变正式数据面默认值。

## 1. 已确定的选择

目标是测清：VPN 内层已加密的 TLS 正文不再重复加密，能否降低整个程序成本，以及是否损害 TCP-like/TLS-like 外观。不是去掉全部外层加密，不是不校验数据，也不是把普通 TLS 改成乱序协议。

采用 **一次标准 AEAD、正文作为 AAD、短元数据加密** 的实验记录。复用已锁定的 `aws-lc-rs`（当前 Cargo.lock 为 1.18.1），不写 AES/GHASH/Poly1305，不为省 CPU 自造 MAC。正文只认证、不再保密加密，仍需读完整正文计算认证标签；不能把其成本称为零。

先采用测试发生器提供的真实 TLS 字节边界 oracle，量出理想上限。不实现通用 DPI、TCP 重组、端口猜测或“看起来随机就是 TLS”的识别。理想 oracle 不代表已经有低成本生产分类器。

真实业务首次交付、无跨业务 HOL、低 CPU 优先。认证、必要完整性、地址/账号隔离、generation、MTU、固定密文重传和 Stop 保持。实验不在主线/FEC 分支直接开发，不默认启用，不改 FEC 算法。

## 2. 冻结起点和源码审阅

- 分支基点：FEC 工位 `34985d2df47ad9c08ce0828554241515a5704266`，已包含网络分支 `040741820b2f917b5868c285c438d4cc21c6193a`。
- 采用 FEC 分支的理由：具备真实 `--outer-repair=on|off`，且带入新的真实反馈/FEC控制接线和已拥有测试 veth 的邻居项修复。这里不使用 FEC 来贡献恢复或收益。
- 新记录原语应隔离在 `crates/wbd-codec/src/selective_record_experiment.rs`（计划路径），通过默认关闭的 Cargo feature 启用；现有 `record_crypto.rs` 和六个旧 wire oracle 保留。
- 现有记录是 `5B 外头 + 8B protected PN + 加密正文 + 16B tag`，正文固定 kind/marker 为 2B，总开销 31B。每包就地 AEAD，不是纯 Rust 标量实现。不要预设密码学一定是主瓶颈。
- Normal 的发送、恢复预算、M1 缓冲、原始 raw/TUN、Go TLS/bootstrap、认证、生命周期及 fq600/flow256 复用。对照和候选使用同一公共代码，不把历史 292Mbps 和后来的 500Mbps 不同源码/机器当本实验收益。
- 保留上游的真实异常与未测范围；基点中 FEC 的吞吐压力结论不能当作 Normal/OFF 的容量上限。

## 3. 最小、逐包独立的数据模型

第一版只处理现有 Normal 单 lane、FEC OFF、IPv4 内层。两方向分别处理，receiver 不等待任何先前包、分类结果或控制确认。

输入内层包记为 `I = H || B`：

- H 是必须加密的整个前缀，包括 LINK（若本路径有）、IP/TCP 头，以及 B 之前的 TLS 记录头等。
- B 必须是同一个已确认 TLS 加密记录的连续不透明字节后缀，到本内层包末尾结束；允许包含该内层 TLS 的认证 tag。
- 一个包只有一个 B。包内跨越下一个 TLS 记录头、无法确定边界、IP 分片、需要内部多个明密区间或 B 太小，整包回退 FULL，不新增区间表。
- 初始工程值：`B >= 512B`、`H <= 256B`。这是压低固定调用/分类成本的候选阈值，不是网络理论极限。先固定测量，不逐 64B 搜索最优点。
- 内层 ACK-only、UDP/QUIC、DNS、非 TLS TCP、健康/控制记录、首尾保护区、未知流量全部 FULL。QUIC 不伪装成 TLS-over-TCP 候选。
- 首版 padding=0。小包照常立即发，不因等待足够大的 B、组包、对齐或分类而延迟。

oracle 必须标注实际 TLS 加密记录区间，不能只标注应用源明文。真实握手、关闭和测试定义的首尾保护区保持 FULL。建议主用例前后各一个应用 TLS 记录 FULL，记录实际保护字节；“尾部预知”只在离线 oracle 有效，不能声称线上能预知最后一包。TLS 1.3 外头 type=23 不足以区分 app/加密握手/alert。

## 4. 实验 wire：连续 AAD 避免大块拼接分配

实验格式名称 `selective-aad-v1`，独立协商/显式试验配置，不伪称当前生产 V4 wire 兼容。

```text
5B TLS-like header | 8B protected PN | 2B protected descriptor | B | C | 16B tag
                    <------------- 10B HP ------------->

unmasked descriptor: bit15 = mode (0 FULL / 1 SELECTIVE)
                     bit14..0 = encrypted metadata length M
SELECTIVE: plaintext metadata P = kind(1) || H || marker(1); B remains unchanged
FULL:      plaintext metadata P = kind(1) || I || marker(1); B is empty
C, tag = AEAD(key, nonce(PN), plaintext=P,
              AAD=unmasked_outer_header || PN || descriptor || B)
```

单条 wire 开销为 **33B**，比当前多 2B，不藏在吞吐分母里。FULL 和 SELECTIVE 具有同样的外层长度公式。descriptor 没有额外明文 magic；仍不意味着不可识别。

这个布局让 AAD 是一个连续 slice，直接交给当前 `Aad::from(&bytes)` API；无需为每包把 AAD 重新拼成 Vec，也无需新增 C/unsafe 分段密码接口。加密数据位于连续尾区，可用 `split_at_mut` 分离 AAD 与密文。只调用一次 AEAD 和一次 header protection，不做两层 AEAD。

HP 采用现有 suite 对应实现，实验域独立派生 HP key，样本取最后的 16B tag，生成 10B mask 覆盖完整 PN 和 descriptor。AES 取一次块输出前 10B；ChaCha 取现有规范的同一 mask 流前 10B。不能截短 PN、复用一次性 MAC 密钥或引入 nonce 冲突。需独立向量、篡改和跨模式测试；此处是协议设计，不是密码实现已通过证明。

发送次序：分配当前 generation 的 PN → 确定 FULL/SELECTIVE → 写 unmasked header 和 descriptor、B、P → 一次 AEAD → 写 tag → HP → 冻结记录 → 原 M4 提交。失败烧掉该 PN，不能换模式后用相同 nonce 再 seal。

接收次序：先对外长度做有界检查 → 用 tag 样本解 HP → 检查 M 与当前 wire 长度关系 → 一次 AEAD 验证 → 认证成功后才使用 kind/H/PN/模式推进 replay、重组与交付。来自 wire 的 mode/M 在认证前只允许有界定位，不改变业务状态。篡改 B、descriptor、头、tag 或跨方向/代次复制都不得交付。

FULL 必须满足 B长度=0，SELECTIVE 满足最小B/最大H和合法IP长度；异常直接失败，不尝试不同算法/模式解密第二次。完整性验证覆盖未再次加密的 B。发送时 B 曾经是 TLS 密文只是分类条件，不是对端可信的替代证明。

## 5. 所有权与 CPU/内存预算

- 每方向一个现有 owner，不新增逐流执行线程、周期控制包或忙轮询。
- oracle 是离线生成的固定 descriptor 数组/有界侧表。主热路径只读取一个 descriptor，O(1) 检查范围。不进入通用TLS解析器、不为每包建立 HashMap 节点。
- 密钥/AEAD上下文每方向创建一次；不同 A/B leg 分离密钥和 nonce 域。按需用原 slab，保持最多32包的现有 batch，不等待满批。
- TX 利用已有 TUN scratch 到 wire slab 的装配机会直接写 B 和短 P，不能先组完整包后又复制整个包来重排；统计实际新增 copy bytes。
- RX 第一版用一个复用 scratch 把 H||B 恢复成原包，或复用现有接收重组目标。**不得宣称零拷贝**：新增的搬移/复制必须算进端到端 B 成本。仅在收益成立且已有安全 driver 接口时再考虑单次 writev；不为了理论零拷贝改整个 TUN 层。
- SELECTIVE 比 FULL 的额外常驻工作区初值 <=256KiB/方向：一个最大record scratch、一个最大IPv4输出scratch、短元数据工作区和固定状态；oracle corpus/发生器内存单列。热路径除已存在 slab/record 所有权机制外，不增加逐包堆分配。
- 不另加 RTT 长度的正文缓存；ACK、重传和回收仍用原实现。原外层重传若启用，同一外层 Seq/PN 的 frozen bytes 全部原样复用，不重新分类、重排或加密。
- 当前重复内层密文在不同外层 PN 下可能原样再现，这是 SELECTIVE 设计的可观测性质。不能用填充、日志过滤或只报告无损来隐藏；如需再对 B 全长变换消除此问题，必须重新计价，不能仍宣称“正文不加密”。

## 6. 接线和复用边界

先做独立 record 成本工具，不碰生产默认。工具必须同时调用真实当前 record sealer/opener，而非用 memcpy 假冒基准。

有足够收益后才接原 Go bootstrap → Rust → raw/TUN 的实验路径。沿用一次真实 TLS 建连和证书处理；实验格式在既有认证后的 bootstrap/cold 配置里显式确认双方能力。不能只靠端口、试解密或静默切换；不支持就拒绝本实验连接。实验开关只在实验构建可用。

数据流形态不变：一个 lane 内混合多条业务；接收端不需要知道哪条内层流被分类成TLS才能解包。每包都有自含、受保护的模式与长度。完全不修改外层 Seq/ACK、重传政策、keepalive或lane切换逻辑。

理想 oracle 侧表仅在 Actions 测试环境存在，不是线上协议字段。内层标签/捕获密钥不通过外层明文发送。以后若做真实分类器，遇到未知立即 FULL，不等待重组，不把分类器的成本从产品 CPU 中扣除。该阶段不属于首轮实现。

## 7. 统一 MTU：多出的 2B 如实计入

通用公式：`inner = effective_outer_mtu - actual_outer_IP_TCP_headers - actual_record_overhead - actual_LINK_overhead`。同时受真实接口、对端MSS、协商record上限约束，复用统一预算入口，不另造1280/1180或减100的常量。

当前 IPv4外层40B、Normal无额外LINK分片头、record=33B、内层IPv4时：

| outer MTU | 内层IP MTU | UDP payload | TCP无选项payload | TCP timestamps payload |
|---:|---:|---:|---:|---:|
|1500|1427|1399|1387|1375|
|1400|1327|1299|1287|1275|
|1280|1207|1179|1167|1155|

IPv4内层低于1280不等于违规IPv6；当前实验不支持IPv6内层。若实际有外层选项或LINK头，重新计算。FULL fallback不能退回旧31B造成同lane解释歧义。

500Mbps应用UDP/1399B约44,675pps，外层约536.10Mbps；500Mbps应用TCP/1375B，单向DATA外层下限约545.45Mbps，另有反向ACK与控制。500M应用测量使用原700M外层，不把500M线路当500M净应用容量。600ms RTT的500M业务BDP约35.76MiB，是业务TCP窗口参考，不是新增cipher工作区要求。

## 8. 四种对照，不混淆收益来源

- A：当前生产完整AEAD、31B格式。
- A-layout：实验33B格式，但所有包FULL；测清新格式/布局/HP/装配的附加成本。
- B：同33B格式，oracle允许的B只认证不加密。其余FULL。
- HTTPS-reference：普通合法TLS下载，仅作为外观参考；不是CPU同功能基准，也不是本项目的外层协议。

A与A-layout/B使用共同可容纳的内层包长，保留真实wire字节差；另给各自最大MTU的效率投影。主要判断是B相对A的实际净CPU收益；B对A-layout只解释减少正文加密本身。不得只公布其中好看的一个。

上限公式：`net_cpu_saving <= aead_cpu_fraction * eligible_byte_fraction * removable_fraction`，再减分类、布局和复制增量。例如0.15×0.8×0.5=6%，是假设上限，不是预测/实测；AAD认证仍遍历正文，不可令removable_fraction=1冒充全部AEAD成本消失。

## 9. 外观与否决条件

保留已有借站TLS建连并不使后续自定义记录变成标准TLS。外层目标IP仍为隧道服务器；TLS1.3证书通常在加密握手中，旁观抓包不保证能直接读证书。内层SNI、DNS、IP/TCP头应不出现在可见隧道正文。

抓包需分别报告：外头结构、握手保持、TCP重传一致性、包长/方向/时间分布、内层明文标记泄漏、不同外层序号下重复大段B。正常TCP相同Seq的重传不能算本实验新泄漏；不同外层Seq/PN的新发送里出现相同长正文必须单列。

**预期反例**：故意触发一次内层TCP重传，若相同TLS正文在两个新外层位置出现，判`APPEARANCE_REGRESSION_REPEATED_INNER_CIPHERTEXT`。即使CPU明显降低，也不合主线；记录结果即可，不为刷外观PASS偷偷增加全长加密。固定外层格式看起来像TLS、熵高、Wireshark识别TLS均不是不可识别证明。

## 10. 来源与复核

- [RFC8446 §5.2–5.3](https://www.rfc-editor.org/rfc/rfc8446.html#section-5.2)：TLS加密记录、真实类型隐藏、每record序号/nonce。
- [RFC5116 §2](https://www.rfc-editor.org/rfc/rfc5116.html#section-2)：AEAD把AAD认证但不加密；本设计使用既有接口而非新密码算法。
- [aws-lc-rs Aad](https://docs.rs/aws-lc-rs/latest/aws_lc_rs/aead/struct.Aad.html)、[LessSafeKey](https://docs.rs/aws-lc-rs/latest/aws_lc_rs/aead/struct.LessSafeKey.html)：连续AAD、就地AEAD。网页版本可能滞后/领先，实际API以锁定的1.18.1源码为准，不为实验追升级。
- [RFC9293](https://www.rfc-editor.org/rfc/rfc9293.html)：TCP字节流与重传；不假定TCP包边界等于TLS记录边界。
- 仓库：`record_crypto.rs`、`record_frame.rs`、`memory/mod.rs`、`v4_embedded_go.rs`、`linux_tun_sink.rs`、原统一MTU/网络夹具，以及[FEC合并起点](https://github.com/lly8666/wbd-next/tree/34985d2df47ad9c08ce0828554241515a5704266)。

实现顺序、场景和实际通过条件见[专项测试](../testing/SELECTIVE_TLS_CRYPTO_TEST_PLAN.md)。当前没有实验结果，结果唯一入口为[本岗位状态](../evidence/selective-crypto-work/status.json)。
