# B103｜正常连接周期与真实共享协议混合业务

B102 SOURCE `559dcdb22782c64af33d65d68547e522e36d45bd` [Action 45535658071](https://github.com/lly8666/wbd-next/actions/runs/45535658071) 19 SUCCESS/0 FAIL/7 SKIP，14/14 scenes、8/8 guest kernel cleanup。真实Android七模式原M4 ordinary App UDP53→物理socket→本地DNS→逆映射TUN→App实际answer PASS；同连接原TCP53 relay PASS。Normal/Game4 CN physical与non-CN tunnel TX PASS，Normal/Game2 tunnel-only TX PASS，远端DNS reply未证。11/11 DNS场原非DNS business TX及Stop。3/3 UID scene，各4次CN/排除/Stop后普通真实TCP+UDP，累计12次各8短TCP、8 UDP、1MiB/方向TCP逐字节echo；不是远端WBD TCP。所有地址仅隔离runner本地持有。B101 579 RAW包0超限与四crash恢复已充分覆盖，不继续极端MTU或异常矩阵。

## B103 正常工况

3独立Android guest，以下每条在同一实际Bionic Go/Rust进程中顺序运行（共9次原TLS/lease/M4 Connect/Close，旧TUN关闭后方进入下一连接；每次Stop后普通App实际物理UDP恢复）：
- Normal + 物理DNS → Normal DNS关闭 → Normal + 物理DNS。
- Fixed + 物理DNS → Auto + 物理DNS → Normal + 物理DNS。
- Game2 + 物理DNS → Game4 Fixed + 物理DNS → Normal CN DNS。
第一连接在已认证M4下，真实普通App使用同一UDP DNS socket每4秒一次，共5次完整答复（至少16秒）；第二次后实际moveTaskToBack并核对window focus消失、记录进程importance，不要求或虚构instrumentation成为真正后台进程。原Rust物理DNS TX/RX delta>=5及error不增长，然后原DNS/非DNS正常业务。此项只是ordinary App Activity切换下活跃native component，非生产RootService READY自动恢复、非外部peer存活判定。依旧是原冷Association进程内transport，raw business远端RX NOT_PROVEN。

另复用同SOURCE x86 Linux原Go/Rust server/client artifact与原LinuxExperiment网络harness，7种模式独立runner，每模式仅一个常用场景：20s 双向10Mbps混合TCP/UDP（各半）、20ms单向延迟、1% IID轻微丢包。实际内核TCP/UDP和真实原TLS/lease/M4，检查双方向双协议均有实际发送及接收、TCP drain无missing，原harness数据完整性/cleanup等判定不变；报告实际原FEC readback而不是预期。Linux结果不能作为Android远端RX或性能验收。无ARM64 Linux重复矩阵、无故障扫参，不改原harness核心/生产代码/主程序MTU。使用原CI同源基础构建，8个历史B102 guest不重跑。

下一大类仍为真实Android↔原Linux物理carrier双向业务、生产RootService READY自动连接/切网、实际热点及ARM64真机；现有模拟器carrier限制保持标注，不以组件结果替代。未操作外部服务器、实体设备、main。历史governance失败未修，B103新SOURCE待CI。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B102 ordinary DNS and direct TCP/UDP; test normal same-process native connection cycles, Activity switch and independent Linux original mixed business reference."}
```
