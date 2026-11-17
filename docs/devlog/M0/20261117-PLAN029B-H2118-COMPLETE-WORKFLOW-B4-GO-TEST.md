# PLAN029B H2118｜修复H2117提交中原工作流命令被截断；真实Windows Go三代纯测试必须执行

H2117 SOURCE `0efa73336f04eb0fbb8e5ef7469f64a6a48fa2c5` 的 [M0-WIN-LINUX Action44122245145](https://github.com/lly8666/wbd-next/actions/runs/44122245145) **FAIL且job=0**；feature catalog [44122249660](https://github.com/lly8666/wbd-next/actions/runs/44122249660)中治理PASS但test_m0_native_ci_scope Python SyntaxError/目录失败，治理维护 [44122249770](https://github.com/lly8666/wbd-next/actions/runs/44122249770)亦FAIL。读取原始Git blob确认：H2117静态Python `self.assertIn` 字符串未闭合；原YAML PowerShell `-test.run=^TestPlan029BThreeGenerationsAdvancedOrdinaryAllNoStaleWriter` 截断，直接吞入下一行原Go test编译，GitHub没有可执行job。这是H2117提交时使用原生字符串替换且replacement中包含特殊 **dollar+apostrophe** 导致JS模板的suffix展开，**不是**Go/测试断言/产品失败。

H2118从已源码锁`a560d3514480e1937a39a5c037dbb6dea643fe6d` 的**完整旧YAML和旧Python静态测试**重新构造两处唯一插入，使用替换回调确保命令中正则结尾符和引号原样保留；创建Git blob后逐字`fetch git/blobs`比对完全一致。原Go测试命令只执行已编好的`client.test.exe`确切`TestPlan029BThreeGenerationsAdvancedOrdinaryAllNoStaleWriter`，无法因`go test -c`单纯编译而得PASS，失败退出码会阻断后续；不装签名网卡、不混跑B4真实GUI场景。真正测试结论必须从**新SOURCE H2118 CI**读回。旧H2117 FAIL保留，H2116 Go/Rust全部编译成功仍仅编译范围PASS，H2112真签名 Wintun /128 IPv6+IPv4/Stop `PASS_SCOPED`不撤回。

B4先进CN→普通CN→all三个真实WinForms OS Applied和各代Stop、晚回调、旧FakeIP实际业务不外发，Game2/4均未验；B5同VM10Mbps CPU/GiB/RSS/p99亦未验，不提前收口029/029B也不开030。

```feature-impact
{"kind":"none","ids":[],"reason":"H2118 repairs malformed H2117 test-runner YAML/Python sources and keeps exact Go B4 unit run gate; no shipping feature/Go/Rust/IPv6 policy change"}
```
