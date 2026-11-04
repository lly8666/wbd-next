# PLAN028 H1096 — Win OS 物理出口切换后的冷 TLS 超时恢复

真正的 `NotifyRouteChange2` / `NotifyUnicastIpAddressChange` 已按 200ms quiet/500ms max 合并，在 `DiscoverPhysicalUnderlay` OS readback 中检查 ifindex/sourceIPv4，只允许源网卡/IP改变后新 generation，旧 Rust/WAL Stop 精确 join。**缺口**：该分支将 `reauthAuthorized=false`，如果新路径第一次 FakeTCP/TLS 因网卡抖动而超时，整个客户端退出；旧条件还禁止 Game2/Game4 进行本类冷恢复。

本次在**原有单一 Windows supervisor** 增 `pathRecoveryAuthorized`，只有经过上述真实OS过滤并已精确Stop旧owner的事件才能授权至多两次既有2秒超时重试；Game2/Game4仅在该类OS事件后获此权限，历史 Health90 行为不改。错误密码（包括 `ErrAdmissionAuth` + Timeout Join）、证书验证失败、用户Stop、首次未授权连接、已应用owner一概不重试，真实新网卡再次变更才重置attempt。无第二恢复器、Go热泵、额外周期探针、数据面wire/MTU计算改变。

同包更新原Go Windows源码、`manifest-plan020-m0.json` exact blob、六条定向Windows Go单测和小Action入口。测试前 `IMPLEMENTED_NOT_TESTED`；此逻辑验证不能冒充真实物理Win NIC切换、Npcap新出口/MTU、首包时延CPU/p99。H998原同连接热缩MTU FAIL、ARM64旧Game4FEC失败、远端ICMP/Android保持原结论。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1096 one Windows original cold generation supervisor permits bounded retry after filtered OS ifindex/source4 change and exact Stop, including Game2/4, with explicit auth/Stop/applied-owner denial, source-locked unit pending."}
```

## H1097 独立夹具及feature schema修复

H1096 首次[Action 41778466223](https://github.com/lly8666/wbd-next/actions/runs/41778466223) 因 Windows 六单测入口工作流错误结尾/重复YAML尾部在工作流加载前 FAIL，Go单测未运行；其他治理检查明确 `feature_catalog.py` 不接受 `UNIT_PASS` 枚举，因此将 H1095 的真实原Go TLS完整握手测试限定标为允许的 `FUNCTIONAL_PASS`（scope 仍为 test-only loopback，不是物理PCAP）。只修工作流YAML与字段，不改变产品Windows Go/Rust源码、route-key或其他Task的测试结论。新Action前H1096仍未获得单测资格。
