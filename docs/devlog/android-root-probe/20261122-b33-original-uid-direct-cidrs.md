# B33｜原Android Root普通App最多4网段真实内核直连／分流

基线为实验 `47276e16`，B32a原 Go/Rust Android dual64＋Linux Oracle＋正式ARM64签名APK [#44969771959](https://github.com/lly8666/wbd-next/actions/runs/44969771959) **11 SUCCESS/4 SKIPPED**；治理SUCCESS，不是手机真实网络E2E。

## 完成的实际产品接线

- **原FIB路由主线**：在B31已同源完成单UID、组选UID、all-app共用物理服务器 `throw peer/32`基础上，直接复用真实内核 `ip -4 route add throw CIDR table 19842`，最多4条显式IPv4网段，首条App UID `ip rule`授予前逐条安装/读回。对协议RAW/TUN包不新增任何代码；FIB只让这些目的地继续执行Android后面的系统规则，**不保证一定通过选中物理Network**。默认不配置就是既有全隧道。
- **原Root journal**：原 `Plan`、`GroupPlan`、`AllAppPlan` 增加可选 `direct_cidrs`，旧journal未有此字段仍保持原精确Stop恢复路径；同一 owner flock、原路由表、UID和持久journal。Stop先删UID规则、再删4个显式前缀和已有服务器/32，再删TUN default，读回后才移除journal。只复用现有单一控制面。
- **原Go CLI**：Android限定冷参数 `--android-direct-cidrs`，解析排序与IPv4规范化，只在已经选择单UID／组UID／全App后允许；真实同一 `androidRootRouteAfterNative` 继承 TLS/凭据/自动/32租约/原Rust M4就绪门。非Android原Linux产品仍拒绝Android专属参数。
- **Root正式App**：真实编辑框→Intent→Service冷复核→原Go argv，非密钥设置导出/导入照旧，无热更新；Host JVM运行生产 `RootDirectIPv4` 格式化与 `RootConnectionSettings` 回读，原签名APK源码门检验完整接线。

## 可验证资格与缺口

Go `rootjournal` Host新测试覆盖三种真实原内核命令、安装在UID首规则之前、Stop释放、失败中途回滚、重复/非法CIDR与外来路由冲突。沿用当前已经存在的 Linux Oracle `go test ./internal/v4productcli/rootjournal` 与 Android Java Source门；仅在**本B33 SOURCE** Actions确实成功后声明HOST_PASS/BUILD_PASS。无设备、无用户真实服务器联机授权，Android实体IPv4直连、原业务TCP/UDP双端内容、系统netd DNS、Game2/4、IPv6/CLAT和性能仍NOT_RUN/MISSING，各自分别标记。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B33原Android Root single/group/all三种UID路由支持最多四个用户CIDR真实私有FIB throw、原持久journal/Stop、原Go冷旗和正式Root App/SAF/Host测试完整纵向接线"}
```

## B33a｜修正历史B11b Host源码门（保持真实FAIL记录）

B33首轮原生ARM64双ABI与DNS/M3 Host成功，但正式APK的 `test-network-scope-gate.sh` 旧B11b静态断言还要求Service调用原Go命令参数以 `fecProfile);` 结束。当前B33真实Service在该同一参数链末尾新增 `directCIDRs`，B11b旧文本检查在测试执行前报告 `AssertionError`，并非原 TLS/Rust M4 运行失败。本次只校正为验证实际当前源 `fecProfile,directCIDRs);`，保留旧Action失败、不删除新B33完整源码门；同一B33a SOURCE需重新由正式APK源码检查、Go route Host、原Linux Oracle建立资格。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B33a校正B11b旧APK静态断言，原App到Go末尾新增直连CIDR参数后合法通过完整源验证；实际内核Route及Go/Rust逻辑不改"}
```

## B33b｜原Go flag定义与App argv的源码检查职责分开

B33a同源原Go/Rust Native和已有Java Host用例继续成功，但B33新增Python source gate把原Go `flags.String("android-direct-cidrs",...)` 误认为源码字符串必须包含命令行前缀 `--android-direct-cidrs`。Go flag定义**本来不含**两个破折号，实际App argv仍明确生成带两个破折号的参数。这是新验收门自身误判；修正为分别验证Go `flags.String("android-direct-cidrs"` 和App `"--android-direct-cidrs"`，并直接核实Root桥三次 `DirectCIDRs`、原路由与App Intent的真实源码存在。旧FAIL历史保留，新SOURCE签名APK／Linux Oracle独立复验，实机仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B33b纠正Go flag无双破折号与App真实CLI argv有双破折号的源码门误断言，保留原Root内核CIDR业务及旧真实失败记录"}
```

## B33c｜最后一处旧式B5参数结束断言复核

B33b [#44975490831](https://github.com/lly8666/wbd-next/actions/runs/44975490831) Java Host/新B33真实接线 SOURCE PASS 后，B5旧源门仍假定 `verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS)` 应在Service内作为参数调用结尾；实际上B33当前真实Go argv继续传递外层MTU、AEAD、txqlen、padding、FEC及directCIDRs。完整扫描同一 Host Python 脚本的 `assert 'literal' in s/a/argv/cold/root_svc/root_ui` 后，仅发现此处仍有旧结尾约定（其余为f-string动态断言/转义字符串）。本批改为断言**完整真实参数调用顺序**，保持原业务代码和同一原Root UID Stop完全不变；旧B33/B33a/B33b失败结果留存，不作Android实机声明。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B33c纠正B5历史源码门对Service参数签名结尾的旧假设；已扫描剩余源码静态检查，直接验证包含CIDR的新真实完整Root argv调用链"}
```
