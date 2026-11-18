# H2173｜Linux双ISA原生测试新版预检误判修正

H2172 [Action44255354198](https://github.com/lly8666/wbd-next/actions/runs/44255354198) 新增的`tests/test_m0_plan029_linux_dual_native_scope.py`本身错误地以严格文本检验`test "$(uname -m)" = "${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}"`，但生产测试构建脚本真实执行反向等价比较`test "${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}" = "$(uname -m)"`，双端真实ISA安全门未放宽。两台原生x86/ARM在cheap step同一测试1/3 FAIL，新的网络未运行。这不是原Go/Rust产品失败；两个历史FAIL如实保留。

H2173仅更正该静态断言以精确匹配严格原生ISA检查，并将本回归测试加入新workflow `on.push.paths`；只有显示标记`[plan029-linux-dual-native]`才启动昂贵真实双网测试。H2171失败诊断的x86 TCP FIN后`getpeername`和ARM64 sudo wrapper READY假阴性修复已在H2172源，不改产品逻辑、FEC、TLS、网络、真实UDP/TCP/Stop验收。再次运行原本唯一两Linux ISA各五短模式，留真实源锁证据，避免散射旧028/029 Windows矩阵。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct a strict but text-order-sensitive native ISA regression assertion in test-only preflight; actual source-locked original Linux product and OS acceptance unchanged."}
```
