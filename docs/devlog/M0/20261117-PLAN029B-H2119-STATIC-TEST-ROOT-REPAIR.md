# PLAN029B H2119｜B4原Windows Go单测门前的Python路径变量NameError修复

H2118 SOURCE `d69a5a0247f05447140b49ce7684e4b54f9aeca2` [M0-WIN-LINUX Action44123359648](https://github.com/lly8666/wbd-next/actions/runs/44123359648) 本次整体**FAIL**，原first-error是`tests.test_m0_native_ci_scope.NativeSmokeScopeTests.test_plan029b_b4_original_go_cold_test_is_actually_run` 在`tests/test_m0_native_ci_scope.py:107`读取`ROOT`时`NameError`。这是新加的廉价静态用例拼接项目根路径错误（文件原有测试均使用`Path(__file__).resolve().parents[1]`）；该跑的原 Windows Go B4 单测被前置cheap拒绝，因此**NOT_RUN**。H2118的工作流已经有效启动Job且治理/功能目录 [44123359542](https://github.com/lly8666/wbd-next/actions/runs/44123359542) 双PASS；治理维护旧FAIL同样如实保留。

H2119只对新测试的两条`ROOT`读取替换为内部`root=Path(__file__).resolve().parents[1]`，原H2118精确源锁`client.test.exe -test.run=^TestPlan029BThreeGenerationsAdvancedOrdinaryAllNoStaleWriter$`仍必须运行，原YAML不改，不解除真实子进程失败硬门。Git blob经新旧SHA读回逐字比对，修复后需真实Windows cheap Go stage PASS才可将B4三代冷构造提升为单测PASS。B4真WinForms三代原生OS Applied/Stop/旧FakeIP隔离和Game仍NOT_RUN；B5同VM<=10Mbps CPU/GiB/RSS/p99未验；H2112 Wintun /128签名 B3限域PASS保持，029/029B未关、030未开。

```feature-impact
{"kind":"none","ids":[],"reason":"H2119 repairs only a NameError in newly added B4 static CI assertion root path; no production source, workflow or feature-status change"}
```
