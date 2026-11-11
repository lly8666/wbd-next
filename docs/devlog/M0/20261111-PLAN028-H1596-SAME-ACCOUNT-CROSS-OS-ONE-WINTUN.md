# PLAN028 M0 H1596｜一个签名Wintun，Windows＋Linux同账号跨设备（非多Wintun）

2026-11-11，用户明确“不需要跑多wintun场景”。H1587旧双Windows原生第二Wintun route/WAL所有权实际FAIL保留，不覆盖、删除原证据、不宣称PASS，标为**同一Windows宿主多个独立全隧道的未支持组合**，本轮不再测试它。**本轮无第二Wintun**。

最新源码ba9599c6的综合治理 `43017950316`、功能治理 `43017950579`、Windows/Linux源码编译和正式装配 `43017950506` 均SUCCESS。H1594 old SOURCE8c0421一个Windows+四Linux五个不同账号的150s原生UDP/TCP＋Win Stop后Bob继续＋共享server/六owner Stop完整PASS_SCOPED；该场不等于已验同账号多设备。

H1596只复用一场现行成熟测试夹具和正式装配，不新增协议/产品默认：Windows Alice签名Npcap/Wintun使用受保护原Go TLS账户`alice`、明确安装ID、自动/32与AES256；Linux Bob通过**同一用户名/口令**的原TLS请求，使用自己成熟Go `--installation-id-file`生成独立持久安装ID，向共享Linux原Rust server申请另一自动/32，验证双方Wintun/TUN OS实际读回不同、Bob在Windows Stop后继续真实UDP。其余三个Linux账号独立，仍覆盖异构AES128/AES256/ChaCha和FEC。五客户端真实双向UDP+TCP150s以及六owner Stop、WAL/netem/WSL资源恢复不降门，场景仅一个Windows Wintun，单独Action `[plan028-h1596-same-account-win-linux-150s]`。

此前宿主4vCPU整体CPU约92.6%且后段outer双向总量下滑，因此仅本场真实应用速率在夹具中调为0.6，六个真实应用都必须last_pace_scale读回0.6。正常产品1460 outer、Normal/off默认、三cipher默认ChaCha、Linux轮换0、Windows keepalive15/dead90/idle0、机会外重传on均不变。新原生Action跑完前这里只能记录SOURCE就绪，不能提前记业务PASS。

```feature-impact
{"kind":"none","reason":"H1596 is bounded native test fixture and CI scene selection for same-account separate OS installations; no product protocol, feature, default or GUI changes."}
```
