# 外层机会式恢复与反馈：现行入口

权威设计为 [机会式v3与MTU](../decisions/NETWORK-OPPORTUNISTIC-REPAIR-MTU-20261023.md)；当前实施/整改读 main registry 和 [主线完工包](../decisions/M0-MAIN-CLOSEOUT-20261028.md)。本页删除旧两次快速恢复/PTO目标的热描述，原文在 [归档基线](https://github.com/lly8666/wbd-next/blob/1bbd2426125bbaeceeb3a16f3a46d5335b198313/docs/architecture/RECOVERY.md)，仅用于解释旧源码。

## 不变的语义
- 新业务不等旧缺口、ACK、repair credit、FEC组或慢lane。首次有效数据立即交付。
- 外层DATA最多一次低CPU机会式修复，原PN/seq/密文不变；没有低损必恢复SLA，不因超时恢复持续DATA PTO。握手/保活恢复独立。
- RECEIVED是可信对端事实；ABANDONED是本地放弃；APPEARANCE_ACK只管外观，不等于业务收到。
- repair缓存、反馈元数据、FEC恢复状态是三种生命周期，不得用其中一个门控所有fresh。
- 预算报F、R、全部外层TX及线路C各自口径；Game副本/FEC parity不是外层DATA重传。稀疏例外和绝对上界按v3。
- 无损重传接近零；高损有限修复不要求UDP残余达到p²/p³。内层业务自行负责可靠性。

## 当前反馈与待完善外观
现代码receipt页从真实认证DATA生成，2ms gap/10ms steady是到期调度，并非每2s质量报告或永久空闲包。Auto本地2s决策、2s/8s成熟窗口是另一层。
现有独立receipt路径不能冒充旧Go质量/keepalive已经统一；主线完工包要求合并ready控制、抑制无新信息、保持payload-idle和固定密文语义，并以record长度/方向/时间关联检查外观。
改变反馈期限必须同步shadow寿命、质量成熟窗口和实际发送证据，不用加密或随机padding替代验证。

## 查实现细节
wbd-recovery 的 receipt/maturity/rx_feedback与对应真实Windows/Linux owner；模块历史契约见 [08-RECOVERY](modules/08-RECOVERY.md)，遇旧两次/PTO/低损恢复要求以本页及v3覆盖。配置、来源和适用资格查功能目录，不从本页推断已测试。
