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

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Game OFF/fixed6 removes unsolicited 250/810ms DATA PTO; genuine authenticated future triggers bounded duplicate cumulative ACK, only real peer gaps nominate frozen cipher, first-send F budget and CPU caps preserved; new-source native tests pending."}
```
