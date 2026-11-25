# B99｜7模式独立RAW wire见证、实际双UID选中/排除/CN、IPv6 DNS

B98a SOURCE `9f3d93a86d99a013de349bd485655d8ecf4d7f2e` [Action 45521294719](https://github.com/lly8666/wbd-next/actions/runs/45521294719) 18 SUCCESS / 0 FAILURE / 6 SKIP。7模式×1280/1460/1500/peer record1200四场景28/28 PASS；OS实际MTU readback全部匹配，56/56临界TX checks，28/28 DF oversize EMSGSIZE、native/UID Stop/TUN close，7/7 guest kernel_cleanup PASS。四个原MTU ABI tests PASS。默认1460时1389/1375/1373/1358，peer1200时1169/1155/1153/1138。B97 Android Fixed接线错误已解决，main共有MTU计算未改；非远端E2E。

本轮 B99 扩大三个独立范围（11个guest，max-parallel仍9）：
- 七模式 peer1200实际临界发送，CI adapter另开只读 AF_PACKET/SOCK_DGRAM 监听选定物理接口 PACKET_OUTGOING，精确IPv4 client/peer/TCP lane src 46100..443 tuple，检查IP total length和TCP payload长度、最大Record/outer及超限数、至少2近边界实际帧。不改原RAW fd、无生产采样/逐包Go、无注入peer或伪造RX。若guest不能观察L2则诚实FAIL，不能凭native计数代替。
- 复用同一Dex构建第二独立package/UID（非KernelSU/Root app），同SOURCE SHA256 APK。single/all实际排除UID向同非CN目的192.0.2.1收独立host-only响应；group实际两个UID分别TUN双socket echo；三场选中UID访问真实CN快照覆盖的1.0.1.1，必须原路由readback不进TUN并收到host-only响应。地址仅隔离Actions host lo上添加精确/32、路由验证、本地socket，退出清理，不使用外部服务。两个UID接管前/Stop后物理回显。若模拟器转发无法到本地别名或CN snapshot不覆盖，独立失败，不能判PASS。
- 原IPv6 system DNS owner enable，真实前台普通App对ULA fd00::53:53的选定Network显式UDP和TCP，检查准确A回答，经实际IPv4 host DNS fixture收据；原 v4/v6 owner Stop和IPv6 RPDB/NAT/iface cleanup。不是系统默认IPv6 Resolver自动选择、不是IPv6 carrier E2E。

未改生产代码、main、MTU oracle、协议、实体机或外部服务器。七模式真实远端 M4 RX、FEC恢复/Applied、READY自动重连、异构lane MSS等仍未证明；不虚构替代对端。B99新SOURCE待Actions，治理历史失败尚未解决。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record 28 actual Android MTU cases and add independent RAW length observation, dual ordinary UID routing/CN and explicit IPv6 DNS capture."}
```
