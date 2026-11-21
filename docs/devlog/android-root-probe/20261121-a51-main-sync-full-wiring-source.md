# A51｜main最新全集成与Android全功能接线审计起点

## 真实源码合并（非假集成）
本轮基点 main `31ce49d9467cde33cce2d61c968129c3173a4b8d`，实验 `1c218d8d78b360b9f1630e939661d48c07f55bb0`，共同祖先 `46a756df1114aecda8dc2d5d259a5cbb4c9a909f`。按共同祖先三方源码对比，101个main-only路径取main blob；383个实验独有路径原样保留。6个共享冲突文件：Rust lib/v4_embedded_go 两端无同行冲突直接拼接；rx_ipv4_tcp 主线已经完成同题最小外层DATA parser，因此全部以 main `parse_data_packet_fast` 为唯一生产实现，Android旧入口仅保留一个无复制委托及A48/A49历史回归；Go admission_v4 TLS注释/行为同题以main为准，两个平台各自真实Admission测试保留；Go v4productcli 合入main的 H2216 policy、Linux server NAT等，保留Android NetId/TUN/Root/UID 原冷控制。main新增 Linux RAW fast、Windows Game READY、H2229 ACK、最新完整工作流与feature-card相应内容原blob不改。本次未修改main、M0 registry或cursor的权威内容，只将其最新原件纳入实验树。

Android源码门同步更新成主线parse_data_packet_fast，不再要求旧 strict pre-M3 DATA parser、旧A49多余的解析函数体。原Rust AEAD/unique PN/replay、原Go TLS及RouteKey、generation/BorrowFence和owned Stop仍由原产品路径负责。旧 Android A48用户真机原Rust `read=1243,data=1229,auth=1227,tun=887,rawtx=887,rtun=1218`，user确认数据已通，但并非最新合并SOURCE的实机资格。A50最新完整产品源码 `a6e4af269bc8402e04fd43d64ecfd4399ca01447` Action #44873613691 SUCCESS，最终doc-only HEAD `1c218d8d` 治理成功；不继承它们的全功能/性能PASS。

## 全功能接线边界与实际开放项
当前 Android原Go CLI 明确拒绝非Normal/off、Fixed/Auto/Game/切网 overlap；原Rust Android M4只实现Normal/off且DNS capture/physical System Resolver未通过冷资格门；Java界面用户可选择App和ROOT启动/Stop，但 UI 默认配置并不等于各功能真实来源。**本次主线合并不伪称 Android 所有模式已接线并运行**。后续最短产品切片是在新源码通过双ABI/签名APK+Linux原Oracle后，逐一打通普通App IPv4所有UID→DNS系统解析→分流/直连→Fixed/Auto/Game→切网恢复、真实Route/Stop。任何阶段失败保留FAIL或NOT_PROVEN，不能因main对应模式已有PASS继承Android。

合并后首次治理源码门发现功能卡 UTF-8 16423B 超过16KiB，A51a仅压缩卡片摘要/限制文字，全部52条历史 verification 保留，旧治理FAIL如实记录。本批完成的是主线全部**源码同步**及共有生产入口的兼容接线。其余真实Android功能尚未实现/复核并明确 NOT_PROVEN；没有部署用户手机、个人服务端或额外dispatch重型诊断。新增功能接线必须在原生产Rust owner中完成，不为“全开关”建立模拟后端。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"按用户要求以main最新共享语义优先将main完整并入实验，Android Root/Go/Rust/UID和Stop保留，共享最小DATA parser统一main；全功能实机和性能资格未继承。"}
```

## A51b｜Go合并测试闭合与Android真实DATA窗口

A51真实合成文件中的Android A38 original protected admission fixture末尾漏掉最后一个Go函数 `}`（语法/拼接问题，原源码测试不删），已单独闭合。主线H2229原Rust外层 `advertised_window:65_535`，Android单真实M4发送 `Presentation` 遗留4096，此处恢复与main一致的65_535，不改加密、路由/Stop、ACK控制包协议或其真机资格。增静态源锁断言，不把主线性能PASS冒称Android性能PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A51合并Go测试缺末尾函数闭合修复；Android原Rust外层通告窗口与main 65535对齐，保留原安全所有权，实际移动网络性能待测。"}
```

## A51c｜保留Android A48实测回归所需的主线builder导入

A51第一轮来源 `1ad36036` 原生双ABI编译 PASS，但Linux original Oracle在Rust `wbd-platform --lib` **测试编译阶段** E0425 `build_presentation_ack` 未导入：main测试模块原只用 `build,Presentation`，本次主线parser上追加了Android A48 ACK反例测试。只在 `#[cfg(test)]` 增加共享原builder的use，不改main解析器本体、生产ACK、Rust AEAD/M3/Route/Stop。旧Action FAIL不改记PASS，新SOURCE需真实回归。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"合并后的Android A48纯ACK测试缺main原builder import，限定Rust测试模块补齐，不改原parser协议；历史CI编译FAIL保留。"}
```
