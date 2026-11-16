# PLAN029 H1960｜同一原 H1958 native artifact 复用真 D1/D2，单 DNS 冷源拒绝不可用地址

## 并行回收 H1958 已经真实运行的 D1/D2
- 独立证据直接来自 [原 Action43792684618](https://github.com/lly8666/wbd-next/actions/runs/43792684618)、SOURCE `ab224ae03cd362f758f98fb59fd097285e436ca6`、Artifact14193726167的 `report.json`，**不重复发 WSL2/native Action**。该 SOURCE 原 Wintun/Go+Rust/Linux的 Stop `PASS_BOTH_OWNED`。
- **D1非CN普通 UDP53**：Windows应用原显示DNS `8.8.8.8:53`，Linux真实Tunnel upstream **1.1.1.1** 只收到目标QNAME一次，原Windows收到源IP恢复为 **8.8.8.8** 的真实A，未造FakeIP。真实黑洞 `no-backup.globalx.example` Windows请求3次，Linux Tunnel收到3次，**物理Direct DNS 0次**，Windows没有伪造/跨方向回包，符合“没有备用DNS/不跨向fallback”的*这一限域场景*。但同SOURCE `app_tcp53=NOT_RUN`、`other_system_dns=NOT_PROVEN`，不能称D1完整退出。
- **D2非CN名字→真实海外IP**：Linux Tunnel DNS给 `203.0.113.77`，Windows非CN请求保留真实A非FakeIP，原Wintun业务回包50字节，Linux真实TUN收到45字节请求（业务方向不同，不应假装相等），物理 underlay不作为该UDP业务出口。**反例非CN名字→CN IP** `cn-ip.globalx.example` 从Tunnel DNS `1.1.1.1` 得到 `198.19.254.2`，原Windows强制Wintun绑定UDP继续向同一真实IP发送，Linux物理收到1次40B、响应40B，FakeIP为false。该IP选择按CN IP并集直连，DNS方向未因CN IP被劫持到Direct。
- **D2 CN正例**：原同一SOURCE CN域名→持久化FakeIP `198.18.0.1`；物理DNS每请求1次、原Linux物理UDP业务收到；另原32KiB真实Direct TCP+FIN回显。**尚缺同一海外共享CDN-IP在CN域名FakeIP Direct与无关非CN域名Tunnel上各跑一条、普通on-link实际捕获、此SOURCE的D1 TCP53**，不能由分别成功的海外/CN地址推断共享CDN隔离PASS。

## 本SOURCE纯冷源 D1 守卫，不改路由或DNS数量
- 同一 `m0Plan029ColdSource` 已拒绝非IPv4、多DNS、组播，但仍接受 `0.0.0.0` / `255.255.255.255` 作为配置的 **direct 或 tunnel 单DNS**，这样的无意义endpoint会让用户以为存在有效上游。H1960只在冷配置验证额外拒绝这两类地址；保留**两个字段相同的正常有效IPv4也合法**，绝不增加备用/第三DNS，也不把各地址按CN IP重新定出口。
- Windows Go的同一现有单测包新增：All/BypassLan/BypassLanCn各模式、direct/tunnel各自无效0或broadcast共 **12个拒绝案例**，以及各模式同一个有效DNS作为direct与tunnel合法的3个正例。不改Rust热路径、Wintun、已有应用，**本 H1960源码待CI**，并非对上述原生D1/D2验收的替代品。
- H1959 Rust Cold FakeIP 0/broadcast及FakeIP目标拒绝与正映射保持的Windows/Linux组件、Go编译、Feature/Governance门已 PASS。H1960只复用原证据与新增Go纯冷验证；后续真实共享CDN/GUI/IPv6需要独立原生正反收件，计划继续IN_PROGRESS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Reuse H1958 exact original signed Windows/WSL2 D1 DNS blackhole no-fallback and D2 CN-IP/overseas business receipts without duplicating native tests; prevent unusable zero/broadcast single DNS endpoints on both cold config directions. Full D1/D2 still OPEN."}
```
