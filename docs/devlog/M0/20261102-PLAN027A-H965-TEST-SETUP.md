# PLAN027A H965｜保留生产未安装Rust MSS即拒绝，修直接Go单测夹具

[H963 Windows编译41475128813](https://github.com/lly8666/wbd-next/actions/runs/41475128813) 编译本身PASS，但随后Linux `TestOriginalColdFakeTCPActuallyRetriesSYNWhenServerNotReady` 直接调用 `NewClientAssociation` 时因`PublicV4AdvertisedMSS`尚未初始化而panic；[H963 Windows原生TLS/WAL41475128735](https://github.com/lly8666/wbd-next/actions/runs/41475128735) 的`TestM0WindowsRealOriginalGoTLSRustM4CreatedWintunSameGeneration`同理在真正驱动测试前FAIL。这是两处历史单测没有产品入口Rust冷初始化，并非允许恢复隐式1360的产品缺陷。

本次只在对应`_test.go`中由测试明确安装`1460-40=1420` MSS，再创建Go association；正式产品仍在真实物理网卡MTU与配置外层约束下调用Rust ABI生成MSS，未初始化则fail-closed；H964更已将历史1360移出生产源。Windows/MSS真实SYN字节/Stop必须由最新SOURCE真实原生测试定论，之前FAIL均保留。

```feature-impact
{"kind":"none","ids":[],"reason":"H965 only repairs two direct original-Go association test fixtures with explicit MSS, no product/source budget or feature state changes."}
```
