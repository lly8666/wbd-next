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

## H2332 · Game 0% 真实重传洪泛：7e 同源码绿色不代表产品通过
- SOURCE `7e2190e` Linux 原始GoTLS/Rust 客户端+服务端 Game2 双向 netem 0%：两端 **各1257 次外层复制**，但首发业务100%且tc无丢包；5%为客户端1250次、服务端1256次。原 Linux Game validator 只在有损要求非零，没审零损R；该组即使Action绿也必须判产品**FAIL**。
- 原 `ack_ever_progressed` sticky 布尔值只要过去曾见累计ACK推进，就容许后续短毫秒重复ACK burst伪装成“长停滞”。本轮改为每次真实认证累计 ACK 改变即重置 `last_ack_change_ns`，同一 ACK 连续 >=1秒加至少3个认证 hints、实发后续字节、原样本仍未 ACK、样本年龄<=2秒、全量首发F的R/F<=10%、最多一次原密文才能提名；绝不恢复周期性 DATA PTO。
- 新原生单元覆盖连续推进ACK但局部4连发的**无损不重传**。Linux 原双向实测 validator 对 Game 无损加包数上限：按真实 `first_lane_copied` 为代理分母，复制包数<=0.05%；仅为保守外观频率代理，不冒充真正wire byte R/F。任何超线 FAIL 而非假PASS。
- 旧7e源码测量不可当新源码修复证据，需同时核收 Windows→Linux Game12、Linux client/server Game18 新SHA和真实 netem/Stop/CPU。

## H2333 · 真实 native unit 在两平台发现第二条 exact-gap 假机会
- 在 SOURCE `53fd6ff` 的 Windows Rust 428/429 与 Linux 348/349 全库测试中，新增 `r1_game_short_duplicate_ack_burst_with_progress_is_not_real_stall` 都**失败**，直接证明第一版只限制稀疏 stall 不足以防洪泛：Game的 exact sampled cumulative gap 分支绕过同ACK>=1秒门。
- main SOURCE `21cff32` 已将 `exact_gap` 也加真实同ACK>=1s与>=3认证重复ACK条件；原早期88ms/110ms提名旧单元更改为认证值持续1秒后再提名。这是保守的表演式外观，首发优先，无DATA定时PTO、无假ACK，原冻结密文只一次，字节上限不变。
- 53fd源码的双端真网和Windows游戏测试即使随后green也不继承本次修复。必须对新SOURCE做新的exact-code unit与0/5/30% Linux/Win Game外层复测。

## H2334 · Game ACK 停滞期内的逐样本洪泛防护
- 仅冻结每PN最多一次**不足以**防止固定 ACK 下每80ms换另一个旧PN持续假重传；主Source `f082e5763eea64397865e35419ba483f2b94cadf` 又加一层**每个真实认证累计ACK值最多一次已实发的原密文外观**；成功实发立即锁定当前ACK，ACK必须真推进后才允许下一机会。无损若ACK因为协议显示停滞也最多一份，不再周期耗CPU。
- 新 `r1_game_one_cosmetic_copy_per_stalled_ack_epoch` 确定性单元：真实首发样本、同ACK持续1s后一次允许，后续又有真实首发仍不得重复；与`r1_game_short_duplicate_ack_burst_with_progress_is_not_real_stall`组合。
- 本SOURCE完整Windows Game2/4 OFF/fixed6与Linux两个真实端0/5/30%未核收，旧7e/53测试不能继承，仍需按新F/R/Stop和0%门判断。高损9%外观为历史目标非任意条件硬下限，安全与低CPU优先。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Game unchanged authenticated ACK >=1s plus one *actual* cosmetic ciphertext copy per cumulative-ACK epoch, no timed replay flood; per-role 0-loss external guard and original 10pct budget preserved; new-source WAN pending."}
```
