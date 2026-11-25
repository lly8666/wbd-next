# B102｜正常工况优先：实际认证后DNS与普通TCP/UDP直连

用户2026-11-25要求：不要防御性搞极特殊工况，检查大类和未覆盖正常工况；停止扩展MTU边界、故障注入等排列组合。B101 SOURCE `0ff84b89e71ae023d048c17d4990a6182fd1badd` [Action 45532853139](https://github.com/lly8666/wbd-next/actions/runs/45532853139) 20 SUCCESS / 0 FAILURE / 6 SKIP。12/12异构Game真实TLS各lane共同client limit1000/server1200、TUN MTU953/938、真实RAW/Stop PASS；原日志12场实际payload包数20+20+42+41+38+38+36+39+76+77+76+76=579，0超限。4/4实际crash退出86、journal durable readback、原RecoverOwned/物理双UID恢复/幂等PASS；8/8 guest cleanup。独立Linux IPv6真实RPDB/NAT UDP/TCP及Stop PASS，Android Bionic relay前轮PASS，Android IPv6 NAT仍内核ENV_BLOCKED。历史失败原样保留。

## 正常使用覆盖及本批决策

- 七模式TLS/lease/本地native TX、MTU、双UID/CN路由、系统Resolver三模式、冷Stop/Restore已有真证据；不重跑这些旧专项。
- 缺真正已认证M4运行中的普通App UDP53物理收发及同连接TCP53 relay；缺原M4域名分流和隧道DNS在实际Android内核上的发送组合；此前系统Resolver专项与Rust数据面分开。
- 缺日常TCP连接/数据（先测可真正闭环的CN直连及排除UID物理流量）。已有普通App UDP回显，未证明全隧道远端TCP/UDP双向。
- 最大剩余正常工况：实际Android与原Linux server标准RAW建链后双向TCP、UDP和DNS，实际READY后的切网/重连/模式切换、后台持续业务，真实普通热点客户端转发；实体ARM64新SOURCE资格和同环境性能仍待验。现有KSU emulator carrier限制不能用人工伪造对端或组件PASS顶替；不复活旧M2逐record receipt。

B102 只改CI夹具/文档，不改生产路径。8个独立guest（5 DNS shard+3 UID shard），11个已认证DNS场景：
1. 七模式原M4 physical DNS：真实原Go TLS/lease、App普通IPv4 UDP53→原Rust selected Network物理UDP→runner DNS fixture→原M4逆映射TUN→App完整DNS答复。原计数TX/RX增长、无新error。再以普通App TCP53→原kernel NAT/Go冷配置relay→同fixture回答，核对host UDP/TCP实收；无外部DNS。
2. Normal/Game4 CN split：本地两类域名的固定小规则夹具（非完整官方库验证，官方库Host证据独立）；CN真实UDP/TCP物理回答，非CN原M4 RAW TX；Normal/Game2 tunnel-only也要求原DNS路径计数和native RAW TX，不伪造远端reply。各场随后发一个普通非DNS UDP并实际native TX，原Stop和cleanup。
3. Single/group/all 三真实路由场：普通App以原测试TrafficProbe对真实CN快照内runner本地/32、被排除UID的非CN本地/32发TCP和UDP，8短消息各自回显及1MiB TCP同时双向逐字节检查。Stop后两普通UID各自真实物理TCP+UDP。每场4次直连试验，真实原TUN UDP witness仍保留作为分流对照，不是原M4远端TCP。
所有外部目的仅Actions runner自己持有，未改main或手机/外部服务器；未称远端E2E、真实READY自动恢复、热点或新实体ARM64 PASS。新SOURCE待运行，历史governance失败未修。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B101 mixed MSS and crash recovery; prioritize ordinary App DNS on active original M4 and real direct TCP/UDP routing, no further defensive edge matrix."}
```
