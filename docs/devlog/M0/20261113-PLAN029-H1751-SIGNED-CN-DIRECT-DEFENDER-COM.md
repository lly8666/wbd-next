# PLAN029 H1751｜H1750签名Direct CN成功与原生Defender单端口Owner施工

- H1750 SOURCE `43d1d00cd7939ec70eb49dcb71eef651a2c29bab` [Action43429931906](https://github.com/lly8666/wbd-next/actions/runs/43429931906) **SUCCESS_SCOPED**：原Go/Rust认证Windows签名Wintun与WSL2原Rust节点，CN QNAME通过唯一物理Direct DNS拿到CNAME/A，先持久化FakeIP再由原Windows应用经物理UDP46111向Linux客体收发，逆向回注准确；原Tunnel TCP/UDP、受控Stop PASS。此前H1749整Action TCP源地址未绑定FAIL保留。本场景不证明新Direct内核TCP/四阶段no-WFP产品全面完成。
- 当前缺口：原Rust post-Apply `PREPARE` 可返回真实Windows kernel listener端口，`ENABLE`要求读回精准Defender Allow与same-generation WAL，尚未存在真实后端。新Windows原生 COM `INetFwPolicy2`/`INetFwRules`/`INetFwRule`，**不启动PowerShell/netsh或复活旧WFP**；用安装/代/PnP/端口hash命名唯一规则，限定IN、TCP6、单lease本地IP、单198.19 synthetic来源IP、一个实际端口、Allow/Enabled/无edge，读回完整字段。
- 新 sidecar 在OS变更**之前**sync intent，真实规则被Add后必须全部字段读回精确，才durable写owned；Stop只能用**同代checksum owned账本**加现场逐字段CAS删除，OS修改但WAL未确认、同名陌生规则、任意规则被篡改、损坏或跨代均保留现场/报错。Windows纯单测注入backend覆盖正常、崩溃、foreign、tamper、跨代及端口拒绝。
- 此次仍仅源码及测试入口，未把新COM挂进原Go产品Stop/Enable；不会用测试通过替代真实Defender逐项可用证明。H1751 Windows Go assembly+tests PENDING，D1–D5/P1–P2/padding仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Preserve H1750 signed CN Direct DNS FakeIP UDP+Tunnel Stop PASS_SCOPED and add native Windows Defender COM exact owned rule and durable intent/owned CAS lifecycle behind inactive real Direct TCP gate"}
```
