# B63｜原M4物理DNS同Network TCP上游回退（Normal/Fixed/Auto/Game）

B61 [Dual64 #45311143807](https://github.com/lly8666/wbd-next/actions/runs/45311143807) 11 SUCCESS/4 SKIPPED，正式签名APK与两Linux Oracle通过。B62 `85d173f6a1628c40d569c39691edfc1d1d7d42e0` [#45311743687](https://github.com/lly8666/wbd-next/actions/runs/45311743687) 按该SOURCE真实CI，治理SUCCESS；实体统一NOT_RUN。

B63复用原PLAN029内核TCP DNS标准长度帧设计及Android已有 `bind_underlay_socket`：原物理UDP53真TC回答匹配当前64槽原查询后，从同一Android Network/ifindex/MTU/源IPv4到同一选定上游TCP53非阻塞连接，原始DNS question/ID不重造。Normal/Fixed/Auto及Game2/4复用现有唯一TX/eventfd的poll（仅有活跃TCP DNS时加FD，最多8个，不增加线程），真实TCP答案仍走B59原UDP逆映射/原TUN分片，尊重原App EDNS UDP cap；失败或答案过大返回原TC，App原TCP53隧道仍兼容。每代原Stop销毁所有待完成socket及64槽。常规DATA不进TCP DNS，不改Go、M3/AEAD/FEC、system netd。Host实际TCP loopback与原事务字节验证；签名APK/双ABI/Oracle按新SOURCE判定，实机和性能NOT_RUN。**这不是直接App TCP53物理接管，不是系统Resolver、热点或IPv6实现**。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B63原Normal/Game M4物理UDP DNS真实TC后同Network同上游非阻塞TCP53回退，复用原eventfd/TUN逆映射，无新包线程；直接App TCP53仍待接。"}
```
