# B121｜设备认证后路由失败

用户上传 B120a (37068bf) Android API36 安全诊断，三次完整连接均已 SYNACK/TLS握手/认证/lease/M4/GO_RX_HANDOFF_OK，进入 UID_ROUTE 后约1713/2025/1736ms失败退出1。故不能解释为这三次服务器域名或Root错误；首次域名失败的细节未保留。诊断只有统一 UID_ROUTE_FAILED，不证明具体子步骤。

B120a Action45625892306 job139246050580 确认低MTU blackhole 真实内核回读含 dev lo，原解析拒绝并阻断新建与旧journal回收。B121只修复该精确等价表示，保留原路由、协议、数据面与B118共享；真实命名空间新增已有journal回收和重启测试。不删除系统表或全局规则。若实机MTU>=1280或其它步骤失败，不能归因于blackhole；新增有限的认证后失败阶段及DNS4/DNS6/IPv6 readiness回执，不记录具体域名、IP、密钥。

此前KSU模拟器Normal使用CI选定UID且未启用新DNS/IPv6开关；新增同生产Service的全App、全量隧道DNS、默认IPv6入口场景，要求实际TLS/业务、UDP/TCP DNS及Stop清理。只跑代表Normal，不扩大全模式。物理设备、热点/USB CN DNS完整链仍待验。治理假红暂不处理。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Correct IPv6 blackhole kernel readback and old owned journal recovery; expose postauth stage and add managed-default all-app emulator qualification."}
```
