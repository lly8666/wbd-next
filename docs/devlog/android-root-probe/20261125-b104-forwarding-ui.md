# B104｜正常使用大类：软件热点内核转发、IPv6 承载及正式 APK 配置持久化

B103 SOURCE `30a78c44a1998b76f1a9c6623596d376966dc8f7` [Action 45538321422](https://github.com/lly8666/wbd-next/actions/runs/45538321422) 21 SUCCESS / 0 FAIL / 6 SKIP。Android三个cycle guest真实同进程3次连接/Stop共9/9，旧TUN关闭及物理UDP恢复9/9；同socket跨真实Activity移至后台5×3=15/15原Rust DNS回复，非生产RootService自动重连。Linux x86七模式独立实际原Go/Rust双端mixed 20s、20ms、1% IID，7/7 PASS_SCOPED_OBSERVATION，双方向TCP/UDP均有实际流量、TCP drain无缺失，不能作为Android远端RX或手机性能结果。不重复B103矩阵，不做罕见工况排列。

## B104 新大类

- IPv4 hotspot组件真实Linux netns：4个独立namespace、真实veth、普通socket。原NewTether完整journal/RPDB/FORWARD/SNAT和DNS PREROUTING，独立下游实际8个UDP+1MiB TCP回显，经business链路时peer验证源地址确为lease；direct CIDR走另一真实WAN路径（peer核对原下游源），DNS实际UDP53和TCP53 DNAT到本地测试DNS socket并返回完整DNS答案。Stop后原业务同目的回到直连，检查原table/firewall/journal清除。所有地址仅测试netns；business veth是原TUN路径的内核组件替身，不是WBD M4/实际手机热点。
- IPv6 carrier组件真实Linux netns：原NewIPv6Carrier client/server两套owner，真实kernel SIT/6rd over IPv4、真实本地普通UID和独立下游IPv6 TCP/UDP、服务端NAT66及下游IPv6 DNS UDP/TCP DNAT。真实peer ICMP6和两端Stop清理。若内核或原产品readback失败如实失败。未改原生产SIT/MTU/NAT。
- 正式ARM64 APK在stock Android API35/36（x86 emulator UI，非ARM ELF执行）用实际UI编辑两套命名服务器配置Normal/物理DNS及Game4 Fixed/CN DNS，显式保存普通设置、force-stop后重新打开并读回、分别载入两槽核对地址/模式/DNS，不发START或联网；同guest普通App原TCP/UDP fixture admission仍单独执行。不是生产READY切换。
- 2个独立Linux namespace任务、2个stock Android guest，并行。只改测试及文档，不修改生产代码、main、实体设备/外部服务器。历史governance失败未修。新SOURCE待CI，不预判新场景PASS。实际Android热点下游、IPv6 Android NAT、原Android与远端Linux RAW/TLS/M4 RX、READY自动切网、实体ARM64及性能仍待验；既有环境限制不通过防御性改产品解决。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B103 normal cycles and real Linux mixed traffic; test ordinary downstream forwarding/IPv6 kernel carrier and actual signed APK profile persistence."}
```
