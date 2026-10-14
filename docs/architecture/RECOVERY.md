# 有界、无 HOL 的外层快速恢复

逐字段、状态机和反例实施契约见[08-RECOVERY](modules/08-RECOVERY.md)。本页给总策略与计算；实现不得自行补出一套累计可靠窗口。

## 目标及不保证的部分

低丢包约 1–5%、缓存和主机容量充足时，尽量在一个额外 RTT 内修补首次损失，最多重传两次。高丢包时牺牲恢复率，保持新业务、延迟和系统可运行。FEC on 不等于“内层肯定补到了”，off 也不是完整可靠 TCP；业务自己的可靠传输负责最终可靠性。

同一包的任何修复必须使用原 seq、PN、nonce 和原密文。新包从不等待累计 ACK、repair credit、接收缺口或 4096 槽。共享出口有有限带宽，修复不可能物理上零影响新包；本设计保证不形成逻辑门控，并限定其占用。

## 1. 三类事实与接收端退役

1. `RECEIVED`：对端确认某个真实收到的 record。释放其 shadow；经过 AEAD 的反馈才有权改变这项事实。
2. `ABANDONED`：次数/寿命/内存/预算已耗尽。只释放本地 shadow，计入原因；不能作为送达成功、不能释放其他缺口的修复资格。
3. `APPEARANCE_ACK`：维持外层 TCP-like 的累计 ACK/SACK 外观。不得当成强可靠业务确认。

RX 首次有效 record 立即进入 LINK/FEC；没有“等 sender 放弃才交付后续”的状态。缺口只留下有限 bitmap/时间戳，重排序窗口过期转 compact。sender 可以捎带退休范围帮助省状态，但不得要求每次 eviction 发一包，通知丢失也不阻止接收退役。迟到、尚未交付过的有效 systematic 在 generation/寿命范围内仍可首次交付；已经交付过的包不重放。旧 generation、身份/地址越界或完整性错误仍拒绝。

FEC heavy 保留原约 3s 恢复语义和到期机制，配合共享字节上限及轻量 compact；不能把“64代”固定移植到高 PPS 新架构。500Mbps、1200B、k20 下 64 blocks 只有约 24.6ms，甚至短于 32ms parity flush，固定代数淘汰会制造故障。纯数量限额改为内存压力处理；时间到期在 BlockID 不前进时仍执行。compact/dedup 也有时间与容量双界，不能无限记住历史。

## 2. 反馈与快速丢失推断

借鉴 RACK 的时间和后到达证据，保留本协议的独立 record 语义。RX 合并发送真实 receipt bitmap：每页 base PN64 + 256bit 位图（40B），通用 body 固定字段上限 32B，单 record 至多 8 页且受当前 MTU 限制。页表示明确覆盖范围内的真实到达，未报告页不等于全部丢失。control PN 与 data PN 可共享递增空间，但只有 data shadow 参与修复。

发现新gap/闭合gap约2ms内合并报告；持续顺序接收约10ms内发送明确received页，没有必须追齐的真实累计前缀。只与同样ready的health/quality合并control bundle，不给每个data追加固定尾、不等待捎带。每页初报加一次有限重复，更新则重新dirty；反馈不eliciting ACK，不产生ACK-of-ACK风暴。静默无dirty则停止receipt；旧keepalive/质量报告仍按配置和idle语义。

TX仅处理bitmap改变的词和其中匹配shadow，用ring完整PN校验定位，不在每个ACK扫整个缓存。未报告页、control/预留失败PN均不是丢包证据。晚到ACK、重复报告、回绕、page覆盖须确定测试；压力后找不到shadow即结束修复，不重新构造/加密。

有至少 3 个后到数据 record 证明且超过时间重排序门限时，首轮 repair 可进入队列；单包/尾包没有后到数据，使用 PTO。严重 reorder 可抬高时间门限，但不能重新引入应用有序交付。第一次和第二次 repair 共享最多两次的总限制，包括 tail probe；每 lane 一次 timer 到期最多挑一个 tail 候选，再重新安排，而非扫尾把所有包复制一遍。

**注意可识别性：**receipt 走独立 AEAD 后的 TLS-like record，不增加每个业务包的固定反馈头；已有 TLS-like 外观测试继续检查长度/方向/空闲周期。反馈不是标准 TCP/TLS 内容，不宣称与浏览器完全不可区分。无需做大规模随机 padding 来掩盖设计问题。

## 3. 带宽预算：精确计数、近似 10% 的含义

初始工程配置：单调时钟的 1s accounting epoch，计数所有 lane 的同一逻辑方向：

- `F`：实际提交成功的首次发送外层数据字节，包括 FEC parity 和 Game 副本，不包括 control/ACK、重传。
- `R`：实际提交成功或已保留发送额度的重传字节，包括 tail probe。
- 一个 repair 长 L 只有满足 `R + L <= max(0.10 × F, 32768)` 才能发。

计数使用同一层：IP+TCP+record 的实际字节，L2 另报；不能分母用应用字节、分子用 wire 字节。发送失败退还 reservation，不重复记成功 F。byte quota 用整数小数余数，不因小包向上取整长期超额。

当该 epoch 的 F≥327680B（约 2.62Mbps），R≤0.1F，repair 在 F+R 中至多约 **9.09%**。稀疏时改用 32KiB/s 绝对额度，**不受重传百分比限制**，单包可重试两次。这个额度是可调工程初值，不是用户硬要求；多客户端共享进程总绝对额度并公平分配，不能每新增一个 idle client 免费乘一份。

另外设置最多 8×当前 MTU 的 burst，repair pacer 按 `max(32KiB/s, 0.1×近期首次发送速率)` 放行；pacer 只能进一步限制，不能绕过上面的 epoch quota。epoch 边界可以把两段短 burst 靠近，**不宣称每一个任意毫秒滑窗都精确 10%**。必须输出 epoch 和滑窗比例/峰值，若业务要求更平滑再收紧 pacer，不引入逐包全历史链表。不能把 10%额度和稀疏额度相加。

两队列都有包时按字节加权服务，初始新发:repair=10:1；每处理一个 repair 后检查新发。repair 队列先临近截止的第一次，再第二次；绝不严格 fresh 永远优先导致低损修复饿死。预算等候初值不超过 20ms，deadline 太近/无额度直接放弃。FEC parity 的首次发送归 F，不伪装成 repair 逃避 FEC 带宽账；另报总 FEC/replica/repair/control 四项。

## 4. 定时和缓存参数

令R=max(SRTT,最近可信且扣除受限ack_delay后的RTT)，V=RTTVAR，A=10ms（顺序反馈允许的最长合并等待；gap的2ms不能冒充全部反馈上界）：

```
W = clamp(R/32, 2ms, 20ms)                 # 初始重排序时间
PTO = R + max(4V, 2W, 4ms) + A
Tcache = max(2×PTO + 50ms, 2×R + 100ms)
Tcache = min(Tcache, 3s)                  # 资源边界，不是假装可覆盖任意 RTT
Nslots = next_power_of_two(1.25 × data_record_PPS × Tcache)
```

RTT 从可辨识的未重传样本取值，遵守歧义排除；反馈携带的 ack delay 只扣除可信且被 cap 的部分。没有 RTT 样本时用 bootstrap 测量和保守初值；不能把 0 当 RTT。两次 PTO 机会已计入寿命，不同时照搬 TCP 无穷指数退避再坚持同一短缓存期限。高抖动/长 RTT 超过 3s 支持范围应报告恢复受限。

V=5ms时：RTT150ms得PTO180ms/Tcache410ms；单程150ms（RTT300ms）得PTO330ms/Tcache710ms。后者不能误写为前者。v1用2ms计算的172/322ms已经被本轮修正；实际间隔以测到的参数输出，不能冻结成所有线路的常量。

按PPS而非Mbps算shadow。初始高吞吐profile一发送方向至多128MiB，总endpoint所有client/lane共享上限512MiB，低内存设备降低有效值；256MiB/方向只能从同一总额分配。分页按需提交，模型采用96B/slot预算：64B hot entry、24B timer node及索引/对齐余量。这是预算而非实测Rust布局；实际size_of、slab rounding、allocator和扩容双代重叠另进manifest指标。

正常策略：先释放确认→到期/次数耗尽→压力下最旧 repair-only shadow。扩容量在控制周期/分页边界完成，不搬移整个活跃 ring。首次发送队列独立；shadow 不够只表示本包可能不能修复，不能制造硬吞吐窗口。多个 lane/client 不各自重复领取全部内存上限。

## 5. 5% 的能力解释

独立同分布丢包 p，原发+至多两次重传且反馈/寿命充足：额外发送期望 `p+p²`，残余 `p³`。5% 时为 **5.25% 额外首次发送字节、0.0125% 残余包损**，因此 10% 预算有余量。它不是突发丢包、极稀疏丢反馈、CPU 过载或大包多个 fragment 的保票。

测试分别报告：第一次交付延迟、修复后的尾部、未送达数量、deadline 内送达率和新包调度延迟。5% 下 p99 可能包含约一个额外 RTT，这是网络修复代价，不是必然 HOL。真正 HOL 门是缺失旧包不能使已经可交付的新包等待；用定向业务序列证明，不拿平均 goodput 代替。

高损场景额度耗尽属预期，允许接近线路残余丢包；仍不得失控重传、内存增长、新包全停或伪造成功 ACK。稀疏场景不强制满足 10% 百分比，验次数/绝对额度/尾包恢复/无空闲风暴即可。
