# H1010｜单端口Game弱网Action失败定位：损伤规则必须按lane五元组

2026-11-03 SOURCE2072554，真实 Linux 双netns Game2 Action 41576418459 / job125720853891 **FAIL**，保留原日志（另见`docs/evidence/M0/PLAN028-H1010-GAME-SHARED-PORT-DAMAGED-LANE-TEST-HARNESS-FAIL-SOURCE207-20261103.json`）。

两侧原Go protected TLS / same port443 / Rust Game M4 Ready、原生Stop均可见，但实际业务0包。原固定fixture在Go/Rust都READY后对客户端下`iptables --dport 443 DROP`、服务端下`--sport 443 DROP`，此前Game按lane开启443/444不同端口，这只坏lane1。H1008已经把2/4条lane都改成**服务端同一个443**；旧规则等于人为断掉所有健康lane，无法判定单lane无HOL。这不是应该改变FEC/重传/OS owner的产品缺陷。

只改真实netns夹具：客户方向`--sport 41031 --dport 443`，服务端方向`--sport 443 --dport 41031`；依旧破坏**同一条**独立FakeTCP lane1，其他Game2/4源port仍合法。用新SOURCE的原同一套Go TLS/Rust真实kernel AppFirstDelivery和owned Stop验收；若再次失败再看真正业务计数，绝不将pipeline绿色或旧UNWIRED假标签算真PASS。

H1008 source207 Game 真实原生 **FAIL** 状态保持，只有后续精确新SOURCE Action通过才能标成功。PLAN027A H998物理在线MTU缩窄FAIL及ARM64 Game4FEC Action FAIL保持。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct lane-specific native netns test injection after single server-port migration; product source logic/feature status unchanged; preserve original failed qualification."}
```
