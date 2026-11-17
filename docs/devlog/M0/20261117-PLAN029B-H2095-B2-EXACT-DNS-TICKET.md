# PLAN029B H2095｜B2原应用四项真回执后NCSI非场景DNS触发假失败

H2094原SOURCE `688193af6b395a36f2916b6c8c53aaa86252b4e0` [Action44071943887](https://github.com/lly8666/wbd-next/actions/runs/44071943887) 原Win2025签名 Wintun/Npcap→WSL2失败，原产物artifact14323013719 SHA256 `285c553911baed9db0a1726b4feee60bfa21e181f052c03077e5bc0f3196b72e`。Windows原AF_INET应用：CN/direct单DNS返回真实海外A/CNAME/TTL2，非CN/Tunnel返回同一A，业务UDP均走Tunnel。Linux真内核分别看到各一有效上游及两条Tunnel UDP；**四项在错误发生前全已出现**，物理业务0。原Go finally`M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS`，但整场本应继续legacy双向TCP，没有运行到，因此整个Action **FAIL**、TCP与完整B2 NOT_RUN。

首错发生在Linux测试自有0.5s linger：Windows自发的 `www.msftconnecttest.com` A `id=a0a3` 进入了**正确**的非CN Tunnel DNS `10.66.0.1`；原B2 Windows脚本只发 `www.globalx.example` `id=6202`，夹具将背景DNS错当脚本查询并RAISE。之前H2093到达双向TCP时才暴露精确Windows临时入站TCP45902 ACL遗漏；H2094 ACL虽已改，但此次未到TCP，不能称已验证。

H2095仅在**原Tunnel DNS**将与本场固定`6202`、CN/global指定QNAME均不相同且合法的真实OS问询作为bounded**非本场**观察（最多四个，首条留存）跳过；`6202`错QNAME、预期域名错lane、物理DNS异名、错误源IP、额外测试重试与重复业务仍fail closed。既不改产品DNS/WFP，也不隐藏异常跨出口。保留0.5s重试观察与原legacy TCP/Stop完整门。下一个H2095源只请求一次`[plan029b-b2-cn-ordinary-real]`真实场景；新SOURCE结果先NOT_RUN。其它B2高级、B3/4/5仍未验。

```feature-impact
{"kind":"none","ids":[],"reason":"H2095 exact source-locked B2 signed test harness ticket scoping only. No product/GUI/Rust/ABI behavior changed"}
```
