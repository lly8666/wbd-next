# 08 真确认、影子缓存与有限快速修复

## 保存什么

一个lane方向一组ShadowRing（扩容时至多两代），slot按完整PN验证，payload指向FrozenRecord。Entry状态`Ready/Flight/RepairQueued/RepairSending/Received/Abandoned`；终态释放一次。两次上限由实际/不确定提交次数维护，不能仅按进入队列次数增加，也不能syscall不确定时当0次。

记录first_sent、last_sent、hard_expiry、seq_offset、attempt、retry_epoch。一次candidate携带(PN,slot_generation,retry_epoch)，晚到/重复candidate不匹配就丢；再发送前复查Receipt/expiry/budget，避免刚收到ACK还重发。Release不能改变fresh队列的可用性。

## Receipt wire和语义（替代v1模糊的累计前缀）

放在00的Control bundle type1。value固定20B：largest_data_pn:u64、ack_delay_us:u32、report_seq:u32、page_count:u8、flags:u8=0、reserved:u16=0；之后每页40B=`base_pn:u64 + bitmap[32]`。base必须256对齐，第i位（字节i/8的低到高位）代表base+i。整包基础32B+40×pages，pages≤8并受当前MTU约束。

bitmap的1只表示认证成功收到，不代表业务可靠协议最终消费；0只对已明确报告的page、且PN≤largest_data_pn范围提供缺口证据。未报告page、未发送PN、跳过PN、control PN不推断丢业务。**没有必须追齐的真实cumulative prefix**，所以失败预留PN/control丢失不会卡住确认。外观TCP ACK完全另外维护。

反馈作用域来自承载它的认证LaneKey和反方向key，不能通过payload指定另一client。report_seq按32bit serial比较，过旧重复不更新RTT；晚来的有效1位仍可幂等释放尚存shadow。报告中的未来PN不能推进发送状态；ack_delay只用于与最大可辨识未重传data对应的样本，受约定10ms上限约束。

## 反馈生成与损失

RX保存分页received bitmap（05复用视图）和dirty/repeat标记。新data产生dirty；gap开/闭合启动最多2ms的反馈deadline，持续顺序data最多10ms；不是每个data启动一个timer。没有data/dirty时停止receipt，纯收到control不触发回执，因此没有ACK-of-ACK风暴。

认证后的重复data不再交业务，也不刷新payload idle，但应请求其page的一次受限receipt重申，解决“数据已到、两份反馈丢失、PTO发来副本”情形。同page最短合并间隔2ms，重复不延长page的绝对保留期；已低于retired floor不重新建历史。这与control不触发回执明确区分。

优先发dirty页，再发未重复的最近页；每页一次初报+一次重复，重复间隔初值max(2ms,min(SRTT/4,20ms))。page又变化则重新dirty，合并全部当前1位。重复保有时间受Tcache/接收窗口限额，不无限重复。队列满/发不出去必须保留dirty或记录feedback_drop，不清空当已报告。

与现有health/quality同一时间ready时装入一个Control bundle；没有现成control也按期限单独发。**不向每个业务record加固定反馈尾，不为等待捎带而拖延业务。** 同batch发送不等于真正省了record头，指标按实际包数算。control自身无repair shadow，但有PN与去重，PN洞被明确允许。

高PPS下8页/报告可能不够，记录dirty backlog/age，增加report频次直到平台/小control预算允许；不能无限加长包超MTU。控制带宽也进总wire账。控制处理过载时停止承诺5%理想修复率，仍保持fresh独立。两次反馈都丢可能导致多余修复，模型p³不包括这种反馈损失，要单独测。

## 丢失推断与定时器

依RACK思想：每lane保留发送时序最大的三个**不同**已确认data见证，以(last_sent,PN)排序。待修slot早于三个见证才获得快速候选资格，不能仅用largest_pn−pn≥3，因为中间可能全是control/跳号。未重传见证的发送至本地收到反馈间隔为R_ack（包含反馈等待）；候选到期为`last_sent + R_ack + W`，到期且见证仍有效才排队。不是要求两个相邻包的发送时间本身相差W；高PPS的相邻包不应因此永远无法快速修复。

首版只用未重传的见证提供时间排序和R_ack；已重传record的ACK仍释放shadow，但不能判断它确认的是哪次发送，不拿它制造第二次快速重发。每lane保存有限的见证，不给每个slot附加后到包列表。该策略比RFC RACK更保守，是有限修复协议，不能标成完整TCP RACK实现。

W/PTO/Tcache沿用总方案公式，PTO的A取10ms顺序反馈上界，不能误用gap的2ms。R_ack用于RACK截止时已含反馈时间，不再重复加A。反馈只遍历changed bitmap词和相关slots；loss检查用发送次序游标/定时器，单轮32候选，不每ACK扫几十万项。未到截止时重调该slot节点，回调再核generation/last_sent/receipt。

第一次repair失败后允许第二次，但必须有**第一次重发之后的新送达证据**，或等last_sent+PTO；同一份旧bitmap不能瞬间连续重发两次。重发候选只入队一次。尾包没有后到证据则PTO触发一个tail候选，两次上限/预算同样适用。硬过期优先于一切repair。

RTT采样只取可辨识未重传record，排除重传歧义；bootstrap无样本用原测量值。收包时间/本地send时间用同端时钟，不用两台未同步机器直接相减。soft queue等待≤20ms，到期额度不够直接Abandoned，不带着所有旧候选等额度无限积压。

## 预算与调度细则

总方案的每1s `R+L <= max(F/10,32768)`保留，所有lane同逻辑方向合并。整数记字节，控制流量不挣F，FEC和Game首发算F并另列放大率。epoch切换不累计旧免费额度，8MTU burst pacer限制边界突发；绝不把10%与32KiB相加。稀疏不限百分比，不是不限次数/任意客户端各领无限总额。

reserve在提交前扣，明确未发送退还，uncertain保留占用，completion重复不能二次记账。quota转epoch时保留在途reservation原epoch账，不能把晚completion记到新epoch赚双份。1s账本用当前+前一在途epoch，超过有界I/O deadline的uncertain标异常并保守计总额。

FEC on时不假设恢复成功，仍按真实record receipt修复；第一版不额外设计逻辑DeliveryACK跨lane取消所有副本，以免又加一套协议。parity/systematic候选优先源包，额度不足时先放弃parity repair；记录这项差异，不把理论模型当全档同概率。

## 必测反例

未报告page、位图尾超largest、未发送PN、control洞、seal失败洞、重复/倒序反馈、两个反馈都丢、ACK到达与repair发送竞态、同一旧证据触发第二次、所有新包持续到来时repair仍获预算、反过来repair洪水不堵fresh、epoch边界/partial syscall/uncertain重复completion、最大缓存/seq回绕/超时后late packet。

参考：[RACK/TLP RFC8985](https://www.rfc-editor.org/rfc/rfc8985.html)、[Quinn packet-space分离与尾探测](https://github.com/quinn-rs/quinn/blob/main/quinn-proto/src/connection/spaces.rs)。不采用QUIC重封装新PN、完整cwnd或有序stream交付。
