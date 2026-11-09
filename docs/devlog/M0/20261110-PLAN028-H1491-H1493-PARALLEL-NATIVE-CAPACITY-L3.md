# PLAN028 H1491–H1493｜三独立Actions加速：容量内阈值 + 两个完整L3原生ARM64

沿当前main `b565c7ea15a9b0df8aac8b643ea8dfdcdd97da85`，M0 H1490和近端Actions无在途业务网测。复用已验 [H1484 ARM原生ISA-L产品artifact13679879171](https://github.com/lly8666/wbd-next/actions/runs/42630288439)，ZIP SHA256 `343b330d2b5f19fd77c8a5bbdd0d70533f51fda1bbbf86cae627d54f244c45cd`、CRC PASS，原native Go/Rust manifest三ELF SHA核对，`SOURCE=57b0d0c` 与原 donor `a7a82db`、ISA-L `c387163f` 不变；只改测试夹具、报告器、Actions，**不做原生架构以外 emulation、不重新编译数据面**。

三个独立原生ARM64 runner并行、每个Action只有自己的一场网络方案：H1491 同VM真实五client 50Mbps（180s 0损、256B/1024B按3:7）稳定控制，原实际独立Go TLS/Rust TUN app、宿主每核CPU/softirq、进程CPU/RSS、共享TUN队列8槽、10ms唯一交付；若50已经存在UDP缺失、overflow、实际发送填充<95%、host均值≥85%或某核≥95%或服务端进程≈1核满，就标容量/产品原因并**不运行**更重75。若50真有余量，再同一VM顺序执行30/50/75/50Mbps四阶段180s，保存原业务/CPU/队列。已知理论50/75Mbps约7875/11813业务包/s，8槽折合1.016/0.677ms仅理想业务到达时间，实际FEC、复制、qdisc、处理与内核内存单列，不能推出产品天花板。

独立H1492 真ARM 1800s 五客户端异构弱网 0/1/5/15/30%及0/15/50/100/125ms；H1493 真ARM 1800s 健康/低损0/0/1/1/5%及0/0/15/20/50ms。都完整原TLS443、Rust M4、UDP/TCP混包、跨五个用户真实轮换、原始六个精确 Stop；0损用户永久UDP唯一缺失仍硬FAIL，高损按实际FEC和相关损伤判断，不虚构零缺。两条目前均**L3 provisional/NOT_RUN**，若H1491暴露未修缺陷或下一轮SOURCE修改，不得把旧源码L3冒充最终资格。

原source66fb H1461 600s Alice DL32 + server pending45、1800s Alice DL351但overflow0仍严格FAIL；H1490已收x86 Game2/Game4限定PASS不重跑；Windows真实Npcap/Wintun最终L3尚未合格、Android/外部物理未跑单列。仅此三项新增测试Action，绝不自动启动029/030。下轮按原始不可变artifact区分 PASS/FAIL/CAPACITY_LIMITED/NOT_TRIGGERED/NOT_RUN；报表错离线修，不重跑网络。

```feature-impact
{"kind":"none","ids":[],"reason":"Frozen source binary reused, three independent native Actions and case-scoped analyzer/fixture only; no product protocol/code/config change."}
```
