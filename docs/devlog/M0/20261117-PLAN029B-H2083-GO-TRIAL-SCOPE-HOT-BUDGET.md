# PLAN029B H2083｜修一次精确Go编译scope和治理热字节预算

H2082 Native ABI44044462134、native-functional44044462254、静态44044462361及原platform假驱动44044462219均PASS，但新Go源 `m0_native_v4_windows.go:1125` 引用仅在cold `if !goSteadyAB` 块里声明的 `trial`，Action44044462149/44044462119真实原Windows Go编译FAIL。H2083只把 `trial.RouteMode==0` 的值复制到同一代外层 `tcpDNSOnly` 后再在post-OS日志使用，**不修改OS Applied/Direct/TCP53/FakeIP效果或安全门**；相应固定原Go manifest里该overlay blob SHA同步，不绕过原编译。

治理失败Action44044462367实际来自 `combined hot byte budget exceeded: 32803`，上限32768字节，不是错误产品源，H2083把旧H2079大文档移出cursor热引用（文件不删），保留关键029B指令/最新日志/证据共7项。

原Action失败及后续候选均诚实留证；新SOURCE原生签名029B B0–B5尚未实测。期待同源Windows/Go编译回归，随后最小真实物理校验而不是旧028极限矩阵。

```feature-impact
{"kind":"none","ids":[],"reason":"H2083 Go variable-scope source compile fix, exact assembly metadata and smaller governance hot refs; product semantics unchanged"}
```
