# A35｜API36三次已发送原TLS载荷却无原RAW对端载荷：精确RST守卫试验

## 真机原收据（用户自行，非CI）
签名SOURCE `c010f7357d0334c48c479012011b6cdb7dad1e4f`，Android API36，V1安全TXT共108事件，包含3次独立启动：
- selected single ordinary App IPv4 UID：`ASSOC_ESTABLISHED`/原Bootstrap载荷TX、15秒`TLS_HANDSHAKE_FAILED_TIMEOUT`，原RAW对端payload NOT_OBSERVED、原Cold RTO OBSERVED、exit1、Owner cleanup。
- all ordinary apps IPv4两次：上述同一结果。真实服务端来源、其RAW接收、认证/lease/M4/真实业务/Stop仍均NOT_PROVEN。不会在上一步TLS尚未验证时用全App IP规则解决报文层问题。

原Linux [Normal/off真实Netns Oracle](https://github.com/lly8666/wbd-next/blob/c010f7357d0334c48c479012011b6cdb7dad1e4f/tools/m0-v4-public-real-linux-netns.sh) 第137–138行明确在客户端与服务端OUTPUT DROP TCP RST；Android原Root Go没有对应匹配规则，初始SYNACK被Android内核视作无TCP socket并生成RST杀死服务端会话是高优先级假设，但尚不是真实设备定论。

## 一批尽可能跨越多个关口的实际修复 + 反例
原Go Android root在首次SYN前先用精确4元组+接口+RST flag的iptables单一规则保护自己的伪TCP接入，不改原raw发送字节/ACK/重传算法、TLS指纹/route key/证书/密码、Rust或Linux产品行为。所有kernel变更在root-only durable 0600 journal、O_NOFOLLOW、flock、comment锁定、`-C`精确读回后方可宣告READY；失败fail closed，不发SYN。正常退出精确delete并readback；进程crash下次经防多owner锁恢复，读回失败保留journal并给显式固定失败事件。测试覆盖安装、计数、Stop、crash恢复、并发锁、外国/重复规则、注入失败与非法接口/IPv4，并在同源码真实ARM64 APK+Go/Rust/Linux Normal/off Oracle验证。

手机TXT仅允许固定枚举守卫READY/RECOVERED、MATCHED_RST_DROP/NO_RST_DROP/COUNTER_UNAVAILABLE、STOP_CLEARED/UNVERIFIED、FAIL(6类)。特别MATCHED_RST_DROP只说明实际匹配规则被内核打到计数，不自动确认来源进程或TLS服务端身份。真实设备用户自行测试前不在其手机或服务器变更iptables。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A35用户c010f735真机三次Original TLS payload TX but no peer payload + timeout；原Linux真实netns依赖双端RST DROP，新增Android仅精确原carrier RST guard及root-only durable回滚与测试，保留真机M4未证。"}
```

## A35a 首轮Host真实FAIL与夹具修复

SOURCE `6b735df99af838c88a9c4f6cbf069b58eed1f66b` [Action #44705679914](https://github.com/lly8666/wbd-next/actions/runs/44705679914) 的 `arm64-native` 前置RST独立Go测试5项均在真正fake iptables执行前FAIL: `RST_GUARD_JOURNAL_UNSAFE`。Go `testing.TempDir()` 当前生成目录权限为0755，生产RootService实际严格0700正确拒绝，因此**仅修单元测试**：给 `privateTempDir` 执行 `chmod 0700`，不放宽真实root-only/0600/O_NOFOLLOW/flock。另修fake runner `-n -v -x -L OUTPUT` 只读计数的参数门，让命中RST证据测试能跑。旧CI失败保留。后续新SOURCE再跑同源Go/Rust、签名APK、独立Linux original Oracle；手机尚未用A35试验。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A35首CI快速捕获模拟Go TempDir 0755误触真实0700安全门，修Host夹具与只读计数解析，生产RST安全边界不变。"}
```

## A35b 同源真实CI第二次：双接线FAIL与完整修复

SOURCE `006be26102dc24175dc062c7228556d9704c8cbb` [Action #44706323960](https://github.com/lly8666/wbd-next/actions/runs/44706323960)：原ARM64 Go/Rust Bionic构建、原Linux Normal/off Oracle、六个Host/M3/DNS Job SUCCESS；真实Go模拟iptables + 0600/O_NOFOLLOW/flock/journal/重启/回滚Host负例已通过。`root-arm64-app` Host Java新报告测试在 `RootDiagnosticReport.stage` 的 `START_DIAGNOSTIC_STAGES_V2 && ROOT_PROCESS_EXIT_NONZERO` 前置事件缺一，仅夹具遗失（用户实际三次报告都有V2）；在A35夹具中补真实V2，并增加READY→MATCHED_RST_DROP→STOP_CLEARED正向组合，明确不冒作TLS成功。`linux-x86-original-server-d2-s0` 源锁Go build缺 `internal/v4productcli/rstguard`（第三套x86服务端装配未copy新包），仅补同原Go包的拷贝、Go Host test与三套装配源静态锚门；绝不改x86产品协议或运行KSU/TAP。两项旧FAIL如实保留，下一SOURCE重新构建签名APK与真Linux Oracle。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A35b把API36真V2安全日志的Java报告夹具及第三套Linux x86原Go源码装配完整接线，保留先前CI红门，不改TLS/内核Root权限。"}
```

## A35 完整新SOURCE产品验收（仅完成证据同步）

真实产品SOURCE `4975c1abf4bc64357f3da246c85dcc15e84d9824` 的 [Android dual64 Action #44707167439](https://github.com/lly8666/wbd-next/actions/runs/44707167439) completed **SUCCESS：11 SUCCESS / 4 SKIPPED / 0 FAIL**。原ARM64双Bionic Go/Rust（x86_64 CI-only）、正式调试签名ARM64 APK、原Java可导出固定脱敏安全TXT/新RST正反例、Linux x86原服务端源锁装配、原Linux Normal/off TLS→真实保护Admission/自动/32租约→Rust M4→真实内核UDP/Stop与标准ClientHello wire审计同SOURCE完成相应CI资格。

原 `linux-original-server-normal-off` Job实际日志含 `ANDROID_A35_FAKE_RUNNER_RST_GUARD_JOURNAL_HOST_PASS`、`ANDROID_A34_ORIGINAL_GO_TLS_CLASSIFIER_HOST_PASS`、`ANDROID_A3_LINUX_SERVER_ORACLE_PASS_ANDROID_RUNTIME_NOT_RUN`；前者是安全的Host假iptables Runner +真实Go journal/权限/Stop逻辑回归，**不等于Android内核真实iptables已安装**。四个SKIPPED依次是旧x86 KSU native、ARM64 NativeBridge、D2-S1、TAP guest；Cuttlefish只有host admission，不等于guest Android业务。

[同源签名ARM64 APK #14614874457](https://github.com/lly8666/wbd-next/actions/runs/44707167439/artifacts/14614874457)，[同源原Linux Oracle工件 #14615856933](https://github.com/lly8666/wbd-next/actions/runs/44707167439/artifacts/14615856933)。当下唯一最新真实用户手机证据依然是旧 `c010f735` API36三次：原Association Established→真实Bootstrap payload TX→peer payload NOT_OBSERVED/RTO→15s TLS Timeout。**A35 root iptables可用性/规则精准读回与计数/内核回程、TLS/认证/lease/M4/应用业务、Android完整joined Stop全是 NOT_RUN/NOT_PROVEN**。无法仅因CI 11绿称真机解决；也不把历史 [#44705679914](https://github.com/lly8666/wbd-next/actions/runs/44705679914)、[#44706323960](https://github.com/lly8666/wbd-next/actions/runs/44706323960) 的 FAIL 改写。本次资料专用SHA并非APK产品SOURCE。

下一次由用户自主仅选择单个测试App UID、Normal/off，先确保旧owner/rules无残留并Stop；使用SOURCE `4975c1ab` 的签名工件进行**一次有界运行**。如果 `ORIGINAL_GO_COLD_RST_GUARD_FAILED_*`，必须保持fail-closed/不继续发SYN；若 `_READY` 且匹配_RST_DROP，判断原内核确匹配到抑制规则，但对端身份仍未知；随后看标准TLS/认证/lease/M4/真实业务和 `_STOP_CLEARED`。若 `_STOP_UNVERIFIED`，不得连续重试或手动flush全局表，优先原owner精准恢复。运行期间有额外**极窄OUTPUT RST DROP**，属于实验性root内核改动，不宣称普通手机无风险。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A35产品同SOURCE 11 SUCCESS/4 SKIPPED：原Go RST守卫Host、签名ARM64 APK、Linux真实TLS/lease/M4/Stop Oracle，真实Android安全/业务仍NOT_PROVEN。"}
```
