# M0 H2330 · Game 外层重传向 Normal 真实缺口语义收敛
2026-11-23 使用 main 前次实测，Linux Game2/Game4 OFF/fixed6 在 0% 和30% netem 都几乎固定复制数（如 Game2 388、Game4 约776）；Windows FEC6 在无损仍复制1500–3000次。虽然原PN/原密文真实、双端Stop成功，却不是 Normal 的无损接近零、按真实丢包机会提名的TCP-like外观。历史9%是高损目标非强制下限；低CPU/首发、真实ACK与10% cap优先。
- Linux Game raw M4 的生产 `on_firstsend` 不再 250ms 无条件 due；仅经过 AEAD 认证的 reverse ACK，且正确索引到原确切缺口并达到原重复ACK阈值时，才令所持冻结密文 due。无损无复制新 r1 单元，既有旧孤立 helper 测试不作为生产资格。
- Windows GameFEC ReceiptState 统一启用 Normal opportunistic_v3，取消810ms无缺口 DATA PTO；1/2选中可选 FEC shadow，**所有**实际首发DATA照常向全局预算记F。Health仅推进不索引；ACK缓存容量不足不保存孤立shadow；Game OFF/FEC都需exact head。未伪造ACK、FEC parity也不当重传。
- 阶段二将Game2/Game4两个真正RX owner的**新认证后到记录**反馈为10ms合并的重复累计ACK，再按同源码原真 Windows↔Linux、Linux client↔Linux server 0/5/30% Game2/4 OFF/fixed6 复验；现有旧SOURCE12/18组仅基线，不能继承修复后的PASS。真实可复用原始二进制仍需严格源/哈希一致。
## Game 两端 native 认证后到记录的低频重复 ACK
- Shared `NativePresentationAck::authenticated_future(seq)` 仅观察原Game AEAD/PN已认证、且原Kernel TUN已提交成功的后到包，非业务ACK、非人工丢包标记。新变更只在现有 TX worker 每10ms最多一次发送累计重复ACK；零后到、零变化绝不发闲置轮询ACK或DATA PTO。
- Linux Game2/4 FEC OFF/fixed6 两处真实TUN提交分支以一组每lane atomic代替额外每记录控制通道；Windows Game原Wintun成功和延迟FEC完成分支也更新一个atomic，NPF前缀成功后才结算已发送ACK。不允许虚构未协商SACK能力。
- 原生选择器将 `r1_game_duplicate_ack_only_on_authenticated_future_and_10ms` 加入原engine unit；新SOURCE真Windows↔Linux与原Linux双端真网、真实受损F/R/C和CPU不继承旧测试PASS。

## 抽样修正
- Linux Game原 1/16 抽样在真实30%高损的首个缺口落在未抽样位置时，后续即便重复ACK也无法准确提名。与 Normal 一致改1/2 有界抽样，按每lane原 M4 firstsend count 做一个位掩码判断；最多一个实际冻结shadow，不回头重加DATA PTO，旧M2每record控制不可复活。验证中不得承诺能强制达到历史9%下限。
- 已调整来源锁定的 r1 单元，以第二个真实copy的 PN2/Seq 作为 exact ACK head；无损即使过1秒也不得补发。

## 真实 5%/30% 双端失败后的机会式补救
- 新Source `fd0c92a63ae54ac73d4bc71edd3b71469d28353f` 的真 Linux Game2 原 Client 与原 Server 在0%没有重传（PASS），5%/30%业务与netem/owned Stop均真实，但两端 `outer_data_retransmitted=0`，验收失败。原因是TCP累计ACK卡在首个**未抽样的真实丢包位置**，后续真实认证重复ACK无法提名任何候选；这正是把本来只为表演的外层重复发包当成真实修复，导致所有高损样式为零。
- 新实现不伪造 ACK/SACK，也绝不无条件定时DATA重发。仅当原 Game AEAD 确证的逆向DATA持续携带同一累计ACK（3个真实重复样本），且该流曾有实际原始首发在候选后面，允许从**仍未被累计ACK确认**、不超过2s的可选冻结样本里按低频率复制一次，哪怕最早缺失记录未被抽样。初始ACK在至少1s以后才能认作稳定停滞，避免0%场景的250ms×2真实RTT误判。没有原数据复制就没有重传机会，累计确认/重排保护/字节预算照常卡死异常发包。
- 复制不解码、不发FEC parity、不创新PN、不抵业务丢包；每lane 80ms限频，全量源实际字节F与已实发R共同判定R/F≤10%。补充 (r1_game_stalled_real_ack_allows_unacked_sample_not_exact_head) 单元。新源码Game 0/5/30 重新实际双向验收，旧Source失败不能冒充新PASS。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Game OFF/fixed6 removes unsolicited 250/810ms DATA PTO; genuine authenticated future triggers bounded duplicate cumulative ACK, only real peer gaps nominate frozen cipher, first-send F budget and CPU caps preserved; new-source native tests pending."}
```
