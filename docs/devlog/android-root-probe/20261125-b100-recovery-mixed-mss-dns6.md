# B100｜实际进程退出后 journal 恢复、异构 Game MSS、DNS6 分层验证

B99 SOURCE `9d40a9b2a2b90744af9a706062153af1f5e95530` [Action 45527391628](https://github.com/lly8666/wbd-next/actions/runs/45527391628) 21 SUCCESS / 1 FAILURE / 6 SKIP。7/7独立 AF_PACKET 真线上长度，Normal14/Fixed25/Auto23/Game2 21/Game2Fixed43/Game4 36/Game4Fixed77，合计239 TCP payload包、最大record1200/outer1240、0超限；Game全部lane有包。三UID实际组/排除、5500 CN真实快照本地目标回显、双普通UID恢复 PASS，10个guest均cleanup PASS。[DNS6 138915275621](https://github.com/lly8666/wbd-next/actions/runs/45527391628/job/138915275621) baseline ip6tables legacy nat Table does not exist；NOT_RUN，非解析失败，未假称通过或禁用Android网络策略。

B100不重复B99成功专项，9个guest+1独立host：
- 4种实际原route/DNS owner install、普通App TUN echo（DNS另有原系统Resolver查询）、进程os.Exit(86)故意不走Stop，shell实测独立进程exit及遗留journal/kernel rule；另一真实root进程调用原RecoverOwned/RecoverDNS/RecoverSystemDNS，普通App恢复物理回显、重复Restore幂等。测试进程退场，不是RootService完整READY自动重连；不清空全局规则或手工伪造journal。
- Game2/4 off/fixed各两种peer SYN MSS顺序（1000 first或last、其它1460、共同认证record1200）：原faketcp server真实SYNACK通过原构造器冻结MSS，原Go TLS与native group，要求TUN按最小MSS OS回读、临界发送、真实线上所有报文在共同1000上限。代码审计发现Android逐lane ConfigureTunnelMTU callback可能被后来的较大MSS提高，原Rust Game组预算以认证record为依据；本轮保留原路径先实际复现，失败才定点修复，不能直接宣称主程序MTU bug。8个scene。
- IPv6 guest NAT完整捕获保持ENV_BLOCKED，不修改内核；另真实普通App ::1 IPv6 UDP/TCP→原Bionic relay→同一selected Network IPv4 DNS upstream真实响应，Stop关闭监听。独立host Linux netns原生产DNS6 journal+同Android exact netlink rule I/O、真实uid/mark/port53 redirect UDP/TCP、错误UID/mark负例、Stop恢复。Host fixture是端口字节回显，不是Android系统Resolver；二者分层证据不能合并成Android NAT PASS。
- B100 DNS6 loopback测试仅为同一个原组件，未修改产品默认或引入外部端点。原主程序/共享MTU/正式数据面没有修改。尚未解决远端 M4 RX、FEC远端恢复/反馈和READY后的系统生命周期；没有操作实体手机或外部服务器。B100结果待CI；governance历史失败尚未解决。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B99 independent 239 wire packets and actual dual UID/CN; classify DNS6 NAT environment block; add crash journal recovery, mixed lane MSS and split DNS6 test."}
```
