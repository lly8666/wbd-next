# 06 LINK、MTU与大包慢路径

## 正常路径

`FrameBudget`唯一计算位置在codec/path_budget：outer MTU、实际IP/TCP header、peer MSS、record max、31B record开销、是否保留56B FEC、Game16B封装。Normal auto即使当前off也按最大FEC20预算保留固定TUN/MSS包络，避免升档后突然超MTU；fixed/off才能使用更大off预算。不能在多个模块各减一次同样开销。

原包≤LINK frame budget且不撞保留magic时，直接移动handle，不加新头。Game先加16B逻辑envelope再进入LINK。启动padding是额外动态字节，只能利用当前剩余空间，不能挤掉已经确定的业务包尾部。

## 兼容分片

保留旧20B格式：magic8=`WBDLFRG1`、version1、reserved0、index:u16、count:u16、total_len:u16、packet_id:u32。所有整数大端。`chunk_budget=frame_budget−20`，除了最后片外chunk长必须一致，count=ceil(total/chunk_budget)。tx保留单个packet的budget快照，换MTU不改变已经切出的其他片。

原内容以分片magic开头需要escape，即使只一片；Normal auto/off原内容以`WF`开头也escape，避免动态FEC识别歧义。固定off不凭`WF`猜FEC。RX分派必须依据协商模式和认证后的内容，不从未解密数据猜。

packet_id32内部扩展为64，跨generation隔离，0保留；回绕时不能复用仍活跃ID。最大逻辑packet仍65535B；Game包络使业务上限相应减少，TUN/IP合法长度校验发生在加包络之前。超过可表示总长明确PacketTooLarge，不能u16截断。

MTU在中途降低时，同一packet_id不能把后半包换成新chunk stride。尚未提交任何片时可丢弃未发计划、使用新ID按新预算重建，已预留PN仍不回退；已有片发送则只在仍容纳旧片的lane完成，或有计数地放弃该大包，后续新业务立即用新预算。已冻结密文不改长、不重seal。大包分片生成也受owner单轮工作预算约束，不能一次处理整个64KiB输入拖住其他普通包。

## RX重组

ReassemblyTable按(tunnel_epoch,direction,packet_id_ext)查slot，默认保留原16个并发assembly、约1MiB payload预算、5s TTL、10s compact TTL；这些仅慢路径初值，不构成正常小包窗口。每项用预分配`parts[count]`+received bitset，count按当前合法最小frame budget推导上界，绝不为攻击/损坏的65535个count分配65535对象。

无需等待首片才能建立有界对象，但总长/count/版本须先合法；收到的非尾片可确定chunk stride，其他片须一致。duplicate要长度+内容一致才忽略；冲突使整个assembly失败并保留compact拒绝复活。最后一片齐全后检查累计长度，分配一个连续业务buffer，仅此一次拼接；交付后移compact，禁止把借用parts直接作为会变的输出。

正常小包不进重组表、不开timer、不扫描assembly。每项一个owner timer，首次片起绝对TTL；重复片不得续命。compact按ID/epoch和TTL避免迟到fragment重新交付已完成包。pressure只淘汰该大包状态，不阻止其他普通packet。

末片先到不能把末片长度当所有片的stride；等合法非末片确定后再核全部偏移。完成重组时旧parts与新连续输出同时存在的峰值也计入预算，不能只算其中一份而越过RX总额。受限时明确失败并释放，不为等输出内存锁住普通包出口。

## TUN与真实网络行为

TUN有效MTU在网络配置成功后读回；TCP MSS处理沿用原方案并记录实际SYN MSS。TCP应用一次write64KiB通常由协议栈分成多个TCP包，测试不能把它当一个线上64KiB record。合法UDP大datagram通过旧兼容路径；不能因为大包统计不好就静默禁掉合法普通包。

操作系统允许的TUN最小MTU（原IPv4路径存在576B下限）可能仍大于极小路径的无分片预算。此时设置合法TUN MTU并使用兼容分片，报告实际budget；不能写入非法MTU，也不能继续宣称普通包必定一个record。

DF/PMTU/ICMP错误语义沿用原功能，超限时明确返回/生成合适错误或有计数的drop，不能永久等待。IPv6默认拦截空路由走原策略，不在codec内误当普通IPv4包。外层不依赖IP fragmentation；探测到实际record超过peer MSS就拒绝该发送并报告budget错误。

区分应用UDP长度、内层IP包、LINK frame、record及外层IP长度：IPv4无options时UDP payload上限65507B，不能把65535B当应用UDP payload；Game envelope只扣一次。内层IPv4分片也不是LINK分片，不复用同一重组键。内层DF限制IP层分片，不自动禁止隧道内部LINK分片后还原完整IP包；保留原PMTU/错误策略并验证，禁止外层IP碎片或擅改内层DF来让测试通过。

## 测试

budget−1/等于/+1，outer1400/1500和options/MSS减小，auto off→on不改TUN包络，片乱序/重复/冲突/末片丢失，16个大包满时第17个及普通包仍可控，magic冲突escape，count/total溢出，5s静默退役，MTU变化和rotation并发。高损大包不强制零丢包，但无长期挂死和额外HOL；模型用实际fragment数而非仅datagram数。

复用依据：旧 `pathmtu/budget.go`、`linkdata/datagram_fragment.go`。第一版不换分片wire或引入通用stream重组框架。
