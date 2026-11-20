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
