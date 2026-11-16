# PLAN029 H1963｜补跑本来遗漏的 Windows Go 单 DNS 冷源边界用例

- H1961 原 Windows [Action43796550769](https://github.com/lly8666/wbd-next/actions/runs/43796550769) 已对 SOURCE `3a036d0f...` 完成 exact original-Go overlay装配/Go编译、旧 `TestPlan029*` 用例及 owned Defender CAS 测试；H1962 [governance43796775422](https://github.com/lly8666/wbd-next/actions/runs/43796775422) 主治理及 feature catalog PASS。
- 复核原生编译日志发现新 `TestPLAN029H1960ColdDnsTwoSingleEndpointsRejectZeroAndBroadcast` **并未执行**：现有 Windows native build 主脚本的 Go 运行选择为 `-run '^TestPlan029'`（大小写敏感）。因此此前“Go编译成功”并不证明3模式×2个非法DNS×2个方向12个负例及3个同地址正例通过。**不得把未执行单测记为 PASS**。
- 本 H1963只重命名测试函数为 `TestPlan029H1963ColdDnsTwoSingleEndpointsRejectZeroAndBroadcast`，让原 runner按现有选择纳入；同步精确更新唯一 assembly manifest 的该 `_test.go` 的Git SHA，保留其他138个原 operations、legacy source及已验证产品Go代码字节原封不动，不新增动作或白名单；按原 Windows native-CLI test 的证据检查该具体测试名称出现在 `=== RUN` 和 `--- PASS`。
- 历史H1958的 D1/D2/P2 original true Windows/WSL2有限 PASS仍独立；H1963单测纯冷配置，不是实时物理DNS、GUI Connect/Stop或D1全出口。P1/P2/Game4/IPv6/共享CDN仍OPEN；普通产品提前连接OFF。

```feature-impact
{"kind":"none","ids":[],"reason":"Rename an existing PLAN029 Windows Go test to match the protected original ^TestPlan029 runner selector and update its exact manifest blob only; no product code or feature qualification changes."}
```
