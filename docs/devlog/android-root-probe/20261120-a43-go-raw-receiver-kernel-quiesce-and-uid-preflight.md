# A43｜Android 真机Rust M4之后原Go接收过滤器的直接修复

用户A42 source `0e2abc5704c105e2344cb29d528082e91fc63522` 实机API36安全TXT共117固定事件、两次Start；两次真实Original-Go FakeTCP/TLS（本次TLS服务器证书身份验证关闭）/Protected Admission、内核/32读回、Rust native IPv4/物理网绑定、RAW/TUN attach、M4_STARTED后同毫秒都报GO_RX_FILTER_FAILED，最后原Go exit1、RST完整Stop_CLEARED。未出现Go RX handoff/UID Route/应用TCP UDP。

审阅原Go donor `lly8666/wobuzhidao@a7a82db31fe7` `internal/faketcp/raw_linux.go`：仅6字节MAC/loopback先装以太网16指令端口filter，其他Android非以太接口可以在未装kernelPortFilter情况下成功完成原FakeTCP TLS；旧`ExcludeDetachedData`却要求该位为true并安装复杂Ethernet四元组BPF。日志不暴露原errno，无法断定用户实际接口类型或准确底层错误，但该先后契约确定有缺口。

本批修改真实Android Normal/off客户端：只有原Go protected TLS、确实Detached且Rust原M4 RAW/TUN全部附加后，`QuiesceDetachedClientReceive`才在原Go独有AF_PACKET RX FD上安装一条`BPF_RET 0`内核过滤指令；没有初始kernelPortFilter依赖，也没有Ethernet偏移。Go RAW TX FD仍活着，原`RepeatDetachedBootstrapACK`仍可在单独TX FD送真正最后纯ACK；原Rust RX FD/TUN/真实Crypto/Network不改。Android单冷会话每次会开新Go RAW FD，故该旧RX无复用。Linux client/server继续原`ExcludeDetachedData`精确四元组过滤，不改共享协议。BPF失败照旧真实报GO_RX_FILTER_FAILED、清理，绝不伪报Ready。

同SOURCE Host通过真实Linux内核SO_ATTACH_FILTER（无先前filter、有先前filter并替换）以及实际loopback UDP送达/丢弃、Go TX FD仍存活；纯Linux内核结果不代替Android手机。原A41 /32 readback与A42诊断门继续保留。

**提前检查下一关**：`androidRootRouteAfterNative`、`rootjournal.New/NewGroup`已读；其原实现重新读真实/32、核物理网ifindex/MTU/IP，先durable owned journal再专属表19842/优先级9600的普通UID路由，逐条真实OS读回，Stop精确逆序恢复，全部非main-table。当前手机为`ROUTE_SCOPE_SELECTED_APPS_IPV4`，非all-apps，故`server_ip_exclusion_readback=NOT_OBSERVED`与此阶段无矛盾。不能从原Host测试预测Android toybox/ip/netd真实行为。下一次设备只需单UID/Normal/off同SOURCE，先检查`GO_RX_FILTER_OK→GO_RX_HANDOFF_OK→UID_ROUTE_ENTERED→UID_ROUTE_RECEIPT`；之后真实APP TCP/UDP+owned Stop。认证证书身份校验仍待严格模式资格验证，不虚报全程PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A42真机两次原Rust M4后旧Go RX filter失败；A43直接修原Go旧客户端接收FD的内核过滤器，并以前瞻UID私表/owned Stop审查和真实内核Host收据锁定。"}
```

## A43b 当前CI真实失败的修复（保留红证据）

A43 SOURCE `ea1713a190d30392f799423faf1c41cb29f5fe73` 自动Action [#44751133369](https://github.com/lly8666/wbd-next/actions/runs/44751133369) 的`root-arm64-app`真实FAIL：`test-network-scope-gate.sh`在`bash -n`阶段发现新Oracle脚本缺闭合单引号，尚未构建APK/运行新真内核Go测试。本提交只将该Go test命令改为无需shell引号的单行调用，并恢复真实PASS marker；原生产Go/Rust和本机Android观察均未改变。旧FAIL保留，下一SOURCE CI需真实证明完整门通过，不能把源锁成功当手机PASS。

## A43c 同SOURCE治理文件同步

A43b 仅修复真实Kernel Host Oracle测试命令的shell引号错误，不改原生产Go/Rust；因该次提交修改了包含`feature-impact`的devlog却未同步更新功能卡，[#44751911977](https://github.com/lly8666/wbd-next/actions/runs/44751911977) Feature Catalog真实FAIL。本次同步最小功能卡与本节明确实际范围。相同原生执行SOURCE仍为`d4ab1a3d08b519726c55e87fef6f71afa0060587`；这次纯文档提交不触发重型Android dual64工作流，不借文档绿灯宣称手机PASS。

## A43d 同SOURCE整份脚本修正

A43/A43b实际CI红证据保留：新Oracle命令首次出现未闭合引号；A43b仅修好命令本身，但同次插入遗留复制的最后约60行仍位于第一个最终`PY`之后，引发 [#44751911992](https://github.com/lly8666/wbd-next/actions/runs/44751911992) root-arm64-app `syntax error near unexpected token ')'`。本提交按整份文件移除**重复的末尾构建+heredoc**，保留原有两处合法`for role`（donor装配和原双端Go编译）、唯一A43真实内核Test及四组完整Python heredoc。未改 A43 生产Go/Rust及原协议；本Source需自己CI证明签名APK和Kernel Test，不能覆盖旧FAIL。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A43d修复新Oracle脚本尾部重复造成的真实CI脚本FAIL，保留原Go RX production修复与真实Linux kernel test；同提交同步产品功能卡。"}
```
