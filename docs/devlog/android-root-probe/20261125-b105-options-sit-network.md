# B105｜普通设置组合、SIT 冷态兼容、实际 Wi-Fi 重新连接

B104 SOURCE `968bd6509ca60d42bee21590180232e8bdc764d1` [Action 45543122668](https://github.com/lly8666/wbd-next/actions/runs/45543122668) 14 SUCCESS / 1 FAIL / 7 SKIP。IPv4 [真实下游](https://github.com/lly8666/wbd-next/actions/runs/45543122668/job/138966177136) TCP/UDP、SNAT、direct CIDR、DNS UDP/TCP DNAT、Stop后直连及namespace清理 PASS。正式APK stock API35/36真实UI两槽保存、普通设置force-stop恢复、分别载入均PASS。IPv6 [138966176996](https://github.com/lly8666/wbd-next/actions/runs/45543122668/job/138966176996) server NewIPv6Carrier失败 foreign SIT identity，业务未运行。源码核对Linux rtnl_create_link未应用IFLA_IFALIAS而do_setlink处理alias；B105将已成功创建的SIT独立set alias（若失败删除刚创建的接口），既有readback和Stop不变，增加真实ip输出诊断。只修冷启动实际兼容问题，尚未证明根因完全解决。

B105 9个独立专项任务：
- 七个Android guest，每种模式仅一个常用选项组合：AES-128/256、flows启动填充、outer repair on、30秒Health；Game4使用默认宽错峰。实际TLS cold逐lane认证cipher/padding，真实native outer enable读回，普通系统Resolver经原selected Network DNS owner及本地fixture完整回答，同时原native普通业务TX、原Stop/cleanup。Normal/FEC读原padding mode及实际计数，不强称Game padding发送或远端repair/Health反馈已证；不做参数全排列，不改热路径。
- 单独Android Normal活跃已认证M4，在原DNS和普通业务后真实关闭guest Wi-Fi，要求原native PhysicalScopeInvalid读回；Stop后恢复Wi-Fi，以实际ConnectivityManager新handle重新连接并真实DNS/业务TX。若无wlan0或无新handle，独立如实失败/ENV_BLOCKED。是显式新Network连接而非生产RootService READY自动切网；没有伪造callback。
- 独立Linux IPv6 SIT/6rd重新执行B104原真实普通UID及下游业务/DNS/Stop；不重跑B104 green IPv4和UI、不重跑B103混合矩阵。

仍缺Android真实远端RAW TLS/M4双向TCP/UDP及FEC repair、生产READY自动重连、实体热点与ARM64新版本及性能。main未改，未操作实体设备或外部服务器；历史governance失败保留。新SOURCE待CI，不能提前判PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B104 actual IPv4 forwarding and UI profile persistence; correct SIT cold alias setup, exercise normal cipher and system DNS options and actual Wi-Fi reconnect."}
```
