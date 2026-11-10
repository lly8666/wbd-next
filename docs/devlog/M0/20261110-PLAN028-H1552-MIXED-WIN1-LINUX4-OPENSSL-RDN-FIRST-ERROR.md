# PLAN028 H1552｜原始 Win1+Linux4 TLS 证书 RDN 首错和旧预算测试文本修正

源 `4388c00ac6b20615ce7749259c73827fa31f0716` 的新 [Action42859887928](https://github.com/lly8666/wbd-next/actions/runs/42859887928) 主流程仅执行了Cheap unit，原产 `tests.test_m0_wl_native_step_runner` 的静态断言只认旧 `$wholeLimit=if(WIN_LINUX_600)`，不知道H1551在最前增加了精确混合 `1180s` 预算；因此 FAIL_CHEAP_ASSERTION，Go/Rust网络 **NOT_RUN**。H1552只更新该原始长期单测的期望字符串，精确保留旧 `1280/2600/600/780/1020` 分支和新 `1180` 分支，旧场景仍不可获得更宽预算。

H1549原 [Action42857999491](https://github.com/lly8666/wbd-next/actions/runs/42857999491) 两条 Windows2025 真实 job loss0 `129979722785`/loss30 `129979722757` Windows+Linux Go/Rust原装配/编译 PASS、管理路由精确 scope PASS，下一步初始化原始Linux服务端证书就失败：`openssl req ... -subj /CN/wbd-v4.example.test` 缺少 RDN `=`，OpenSSL 返回 `Missing '=' after RDN type string 'CN/wbd-v4.example.test'`。这是测试证书配置，不是产品TLS认证失败；五原生OS客户端应用、600s外层计数 **NOT_RUN**。修成 `-subj /CN=wbd-v4.example.test`，不改原生Go/Rust或真正证书SAN，给H1548定向源码契约补正负校验。Windows宿主防火墙、WSL源邻居完成原始所有权清理且外来路由未被接管。

提交带 `[plan028-h1548-win1-linux4-600]` 触发**一轮** loss0、loss30 独立Windows Runner真实600s；所有原始失败和其SOURCE保留；不会用旧 Linux-only 333.930/304.271 两个PASS代替混合Win1+Linux4的真外层250–300目标。PLAN028仍IN_PROGRESS。

```feature-impact
{"kind":"none","reason":"Only correct test-only OpenSSL certificate distinguished-name typo and update immutable CI native watchdog expectation for the newly scoped mixed 600s case. No production Go/Rust/FEC/TLS wire or route/WFP/owner security changes."}
```
