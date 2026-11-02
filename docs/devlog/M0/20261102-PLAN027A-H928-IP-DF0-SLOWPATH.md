# PLAN027A H928｜首个共用 IPv4 DF0 有界慢路径

Rust `wbd-platform::ipv4_fragment` 新增纯 RFC791 IPv4 DF0 分片，原ID、8字节偏移/MF、源IP options copy bit、IP checksum、UDP/TCP原始业务体不变；输入畸形、DF1、旧片和超32片拒绝（只丢单包）；RFC1191 ICMP3/4纯构造需要受信任本地router IP及控制额度，本批**没有**真实注入资格，不能宣称DF1已交付。原始小业务无变化。

Linux Game2/4 共用一个 M4 TX worker 现在用 **一次** 65,535B 读缓冲避免 TUN 大包截断；仅完整合法DF0单包超内层预算且已有用户态记录时，申请最多32个标准IPv4片，分批4片/轮，同轮优先新小包，使用现有原Game/GameFEC owner/cipher/Stop，不造跨lane/新后台/假LINK。内核正常分片前提不变。原有 Normal/off LINK 保持，Fixed/Auto 与 Windows 仍无此入口；不做不准确全模式承诺。

待冻结SOURCE原生边界构建/真实双端、实际DF1 ICMP OS验证、FEC/Windows入口、两组弱网与保护性能均 NOT_RUN。数学分片单测不等于实际业务F/R/C交付。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Implement bounded RFC791 DF0 IPv4 exception path with option copy/fragment offsets/checksum and RFC1191 pure ICMP encoder; wire Linux Game2/4 existing TX worker with 4 fragments/turn and no fake LINK. DF1 OS delivery and cross-platform native remains NOT_RUN."}
```
