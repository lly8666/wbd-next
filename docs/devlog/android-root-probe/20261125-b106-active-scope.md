# B106｜活跃 M4 与多 App/全 App、真实 TCP 建连发送、Network callback

B105 SOURCE `4957c16ec9cc03ac1a2ace274a447907fac713b0` [Action 45545657277](https://github.com/lly8666/wbd-next/actions/runs/45545657277) 18 SUCCESS / 2 FAIL / 7 SKIP。7/7 实际 AES/flows TLS cold、outer enable、系统Resolver+M4、普通业务TX、Stop；Normal/Fixed/Auto padding实际发送各1 record、347/222/174 bytes；8/8 Android cleanup。Game实际padding字节与远端repair仍未证，不重复参数组合。

B105 [IPv6 host 138974512528](https://github.com/lly8666/wbd-next/actions/runs/45545657277/job/138974512528) 两端SIT alias/6rd/MTU及ICMPv6通过；普通UID setpriv后无法读取runner私有checkout路径，后续业务NOT_RUN，非数据面失败。B106只改测试，root读同一Python源码后以setpriv普通UID执行，不改checkout权限、不以root代替普通UID。继续真实TCP/UDP、下游DNS及Stop。

B105 [Network 138975657614](https://github.com/lly8666/wbd-next/actions/runs/45545657277/job/138975657614) 真Wi-Fi关闭、新handle 432902426637→437197393933、原owner Stop及新连接DNS/业务、cleanup实际PASS；旧native PhysicalScopeInvalid未观察，专项FAIL。原Rust check_scope/recheck主要检查interface/ifindex/MTU，Android Network callback是不同层；不为了将flag变绿而改生产热路径。B106独立真实ConnectivityManager watcher，必须在同一原handle上注册，真实onLost后由CI调用原Stop并显式新handle重连。仍记录native flag，若未观察不称它PASS。不是生产RootService READY自动重连。

新场景：2个Android guest（Normal selected group两实际普通UID，Game4 Fixed all apps排除第二UID）执行原M4 TLS/lease后的生产androidRootRouteAfterNative，真实CN snapshot、真实system Resolver、普通App UDP TX及普通TCP connect SYN TX，CN直连实际TCP/UDP回显和排除App物理回显，Stop后两UID物理恢复。TCP SYN测试明确无远端回复；Normal额外原native TunTCPSeen增长，Game原RawCopied增长。现有隔离runner本地IP和端口，非外部网络。

总计3个guest+1真实host专项；不重跑B105 green选项、B104 green IPv4/UI、B103 green Linux matrix。未改生产代码或协议。仍未证明真实Android↔Linux carrier完整双向TCP/UDP、FEC远端恢复、RootService READY自动重连、实体热点和新版ARM64/性能。main独立推进到634889789436，未merge或改main/M0；历史governance失败保留。B106待CI。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B105 ordinary options; fix actual IPv6 nonroot fixture access, test real Network callback and combined active M4 multi/all App traffic."}
```
