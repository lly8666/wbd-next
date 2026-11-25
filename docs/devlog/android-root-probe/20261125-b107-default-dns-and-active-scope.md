# B107｜正常域名启动/默认 Resolver 与活跃多 App，修 CI 编译

B106 SOURCE `a0d72bc6ffc5b74dbec7c4653580a9d97a1e26a2` [Action 45549418682](https://github.com/lly8666/wbd-next/actions/runs/45549418682) 7 SUCCESS/1 FAIL/12 SKIP。真实 [Linux IPv6 138986741102](https://github.com/lly8666/wbd-next/actions/runs/45549418682/job/138986741102) PASS：两端实际 SIT/6rd、普通UID及独立下游TCP/UDP、NAT66、下游UDP/TCP DNS和双端Stop/journal清理。B105测试降权路径权限问题已解，仍非Android实体热点/IPv6远端M4。公共build [138986741062](https://github.com/lly8666/wbd-next/actions/runs/45549418682/job/138986741062) CI-only b91 helper三处 undefined strings；3 guest未执行。B107补import，保留B106 scope及Network原判据，不再重跑green IPv6 namespace。

新增普通使用组合（复用两个原 guest）：实际选定 Network 物理 DNS 解析服务器名 target.test（本地fixture A=10.0.2.2），用原生产 Run 同一 ResolveBootstrapIPv4WithUpstream 入口，在冷TLS关联前使用解析所得地址；随后已认证M4下真实普通App Java InetAddress.getAllByName（不显式绑定 Network）与已有显式Resolver、TCP SYN、UDP TX、CN/排除直连回显并行验收。两个UID使用不同域名、Host必须有真实查询记录；group 10 probe、all 6 probe。仅CI夹具，非完整生产CLI启动或remote SYNACK/TLS。独立network guest 保持真实原handle onLost/Stop/新handle显式重连判定，native invalid状态独立。增加active_scope收据，未执行或未证不算PASS。

复核 A25b TAP/wifi-TAP真实无RX，SLIRP非raw透传；ARM64 hosted admission无已配置Cuttlefish guest及host tools。未发现已验证新carrier，不重复旧重型探针，不引入替代协议、伪造回复或生产防御逻辑。剩余实际Android远端双向业务/FEC、生产READY自动重连、实体热点/ARM64及性能需要可用实际网络/获授权实体设备。main未改，历史治理失败仍保留。新SOURCE待CI。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept actual Linux IPv6 carrier/downstream; repair CI import and test ordinary hostname bootstrap and default Resolver with active multi/all App M4."}
```
