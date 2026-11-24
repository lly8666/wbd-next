# B62｜后台冷切网、断网事件恢复、配置轮换及通知状态

基线 B61 `8684684ff0417840560adbe5fc303a33afa5bcae` [Dual64 #45311143807](https://github.com/lly8666/wbd-next/actions/runs/45311143807)：查询时双ABI及六个基础Host SUCCESS，治理 [#45311143813](https://github.com/lly8666/wbd-next/actions/runs/45311143813) SUCCESS，APK/两Linux Oracle仍运行。最终资格仅按实际同SOURCE Actions。

本批批量接线：原B61单Service当前连接快照同时支持显式后台自动恢复和定时轮换。所选实体Network失效时旧Go/Rust owned Stop及原UID撤销确认后才能冷重建；优先实际默认物理Network，其次已验证物理Network或唯一LAN-only；没有合适Network时保留前台Service并订阅WiFi/蜂窝/Ethernet真实系统回调，不开包处理线程或轮询。不重试认证失败，不后台开机自启。STOP/Restore/移除任务取消等待/轮换。新Network替换handle/interface/ifindex/MTU/local IPv4，重新求当前DNS和自动LAN直连，冻结的手工CIDR、server/profile凭据不变。原Go FakeTCP/TLS、Admission、/32、Rust M4、原UID同一START；非热迁移。B60前台选择仍可用，与后台模式互斥。

原本地设置/四槽/SAF codec增加0关闭/1前台/2后台与0/5/15/30分钟轮换，旧预设默认关闭，导入只恢复表单不启动。通知显示M4+UID真实就绪/断网等待，STOP和返回Activity沿用原入口。Host生产决策/设置round-trip、正式APK和Linux Oracle以本SOURCE CI为准。设备、真实E2E/性能统一NOT_RUN；物理TCP DNS、系统netd DNS、热点、IPv6仍MISSING，main/M0未动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B62批量接线后台Network事件冷恢复、同会话轮换、四槽/SAF冷配置、原通知状态；复用原Go/Rust完整Stop/START，无新数据面。"}
```
