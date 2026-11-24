# M0 H2330 · Game 外层重传向 Normal 真实缺口语义收敛
> **PR #68 分支镜像**：main Game 修订 SOURCE `83806f8d3e11822a597b516fae6761929e3e177e` 的机制实现现同步进入本实验分支；本 PR 分支源码需独立测试，不能把 main 后来的 Actions 当成 PR 资格。

2026-11-23 使用 main 前次实测，Linux Game2/Game4 OFF/fixed6 在 0% 和30% netem 都几乎固定复制数（如 Game2 388、Game4 约776）；Windows FEC6 在无损仍复制1500–3000次。虽然原PN/原密文真实、双端Stop成功，却不是 Normal 的无损接近零、按真实丢包机会提名的TCP-like外观。历史9%是高损目标非强制下限；低CPU/首发、真实ACK与10% cap优先。
- Linux Game raw M4 的生产 `on_firstsend` 不再 250ms 无条件 due；仅经过 AEAD 认证的 reverse ACK，且正确索引到原确切缺口并达到原重复ACK阈值时，才令所持冻结密文 due。无损无复制新 r1 单元，既有旧孤立 helper 测试不作为生产资格。
- Windows GameFEC ReceiptState 统一启用 Normal opportunistic_v3，取消810ms无缺口 DATA PTO；1/2选中可选 FEC shadow，**所有**实际首发DATA照常向全局预算记F。Health仅推进不索引；ACK缓存容量不足不保存孤立shadow；Game OFF/FEC都需exact head。未伪造ACK、FEC parity也不当重传。
- 阶段二将Game2/Game4两个真正RX owner的**新认证后到记录**反馈为10ms合并的重复累计ACK，再按同源码原真 Windows↔Linux、Linux client↔Linux server 0/5/30% Game2/4 OFF/fixed6 复验；现有旧SOURCE12/18组仅基线，不能继承修复后的PASS。真实可复用原始二进制仍需严格源/哈希一致。
## Game 两端 native 认证后到记录的低频重复 ACK
- Shared `NativePresentationAck::authenticated_future(seq)` 仅观察原Game AEAD/PN已认证、且原Kernel TUN已提交成功的后到包，非业务ACK、非人工丢包标记。新变更只在现有 TX worker 每10ms最多一次发送累计重复ACK；零后到、零变化绝不发闲置轮询ACK或DATA PTO。
- Linux Game2/4 FEC OFF/fixed6 两处真实TUN提交分支以一组每lane atomic代替额外每记录控制通道；Windows Game原Wintun成功和延迟FEC完成分支也更新一个atomic，NPF前缀成功后才结算已发送ACK。不允许虚构未协商SACK能力。
- 原生选择器将 `r1_game_duplicate_ack_only_on_authenticated_future_and_10ms` 加入原engine unit；新SOURCE真Windows↔Linux与原Linux双端真网、真实受损F/R/C和CPU不继承旧测试PASS。

## 分支镜像：Normal-matching sampling
- 保持Game Linux真实后到/重复ACK驱动，1/16首发抽样过稀不能呈现高损候选；现在改为1/2位掩码并保留每lane单份原冻结密文，零定时DATA PTO。补充 r1 单元，并等待本分支自身 native WAN 验收，旧main SOURCE测试不可继承。

## 新增：首个丢包未被抽样时的真实停滞机会
- main 产品源码 `1cade763d20d15f1550a8e77fa6c6a97373f1fc4` 在此前双端 Game5%/30% 外观 R=0 后，补充 AEAD 确证的真正重复 ACK 停滞分支：至少三次实际逆向数据提示、实际后续已复制首发、初始至少1秒 RTT 稳定、最多2秒旧密文、累计 ACK 尚未覆盖候选、依旧 <=10% F 字节、80ms/lane 有界发送、无 timer-only DATA。
- 当前 PR68 分支只镜像该 **Linux Game 原功能源码** 和精确 unit；main 上新 12 个 Windows Game / 18 个 Linux 双端真实场景为 main SOURCE `7e2190e4bf7a0c643c76eaae4bd4b37c99e470bc`，**不能继承到本 PR 分支**，新分支完整验证仍未通过；旧 M2 逐 record Receipt 继续废弃。

## H2332：PR 专属更正，不能继承 7e 真网假绿
- main SOURCE `7e2190e` 原 Linux client/server 真0% Game2 双端各1257次重传，5%分别1250/1256次；0%绿色 **是假验收**，main 已单独修复。
- 本 PR 实验分支同步相同 **Linux Game产品逻辑**：只有同一AEAD认证的累计ACK不变>=1秒、3次认证重复、后续真正已发、候选≤2秒且R/F<=10%才准一次旧密文复制；任何ACK进展立即重置停滞计时，无周期DATA PTO。内置新的r1单元无损短重复ACK不误报。
- 新主分支来源锁定Linux 18场景、Windows Game12场景不自动证明PR分支资格，PR自身真网状态仍NOT_RUN。

## H2333 · 原生单元追出 exact-gap 毫秒重复ACK误判
- 新增 `r1_game_short_duplicate_ack_burst_with_progress_is_not_real_stall` 实际在 Windows 全库428/429 与 Linux348/349 回归中首次 FAIL。原因不仅是sticky ever-progressed，`exact_gap` 也绕过 >=1s ACK稳定门提名原记录。修为**两种Game候选(exact-gap及稀疏真实停滞)** 均需同一已认证累计ACK不变>=1s及至少三次重复。旧h812测试早期88ms、110ms触发行为本身错误，改为真正保持1s后的时间点；无损持续推进短burst单元必须通过。
- 21cff32是main产品新增修复。PR分支仅同步源码和真实失败证据；PR自己的真WAN另需资格，不能继承main。零损 Game2/4 OFF/fixed6 双端不应有规律外观重复。

## H2334 · Game 新增一ACK最多一份外观
- 原始每PN最多一次仍可在同一冻结累计ACK下连续换PN复制，源 `f082e5763eea64397865e35419ba483f2b94cadf` 又给每lane新增 `last_replay_ack`，**只在同一真实累计ACK首次成功补发后锁定**，直到有认证 ACK 进展才准另一原密文机会；每端80ms限频、10%字节上限、同ACK稳定≥1秒仍保留。
- 新 `r1_game_one_cosmetic_copy_per_stalled_ack_epoch` 与 `r1_game_short_duplicate_ack_burst_with_progress_is_not_real_stall` 必须源锁单元通过。新的main双端测试 SOURCE `60a20196d9c028c20d989232b991a6a0becb30e0` 已发起，PR自身未取得WAN性能PASS。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Game Linux authentic duplicate-ACK stall admits an unacked sampled original even if true first missing head was unsampled; initial >=1s, candidate <=2s, real first-send behind, 10pct cap and one original replay, no timer-only DATA; new-source WAN pending."}
```
