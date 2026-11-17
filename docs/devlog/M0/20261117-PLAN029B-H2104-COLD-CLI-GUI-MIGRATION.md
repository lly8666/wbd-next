# PLAN029B H2104｜H2103签名off回归真PASS；补原Go CLI停用容量校验

H2103 SOURCE `15978946fe382d6f124c64eceb81fcd7de2a2822` [Action44085831814](https://github.com/lly8666/wbd-next/actions/runs/44085831814) / job134050923926 原签名 Win2025 Npcap/Wintun↔WSL2 完整SUCCESS，原artifact14329403547 ZIP SHA256 `b364c172281608bda0b9d4deb1269dcde83f3308472f023360659bd5185c0757`；SOURCE=Linux=WinExe=fixture 均相同。实读`route_mode=0 business_split=false cn_domain_fakeip=false`、只有DNS用途TCP listener(`direct_business_nat=0`)，Windows/Linux真内核双向UDP/TCP回显、TLS/OS/WAL与双方owned Stop PASS。该例仍为旧测试外层1400，**不是**1460新默认资格；无真实IPv6、无10Mbps配对CPU/p99，均NOT_RUN。

H2102的Rust/Go `m0Plan029ColdSource` 已忽略off/all时的旧DirectFlowHard，但回读原Go装配`cmd/wbd-client/main_windows.go`发现独立**更早**的`--check-config`校验仍不分活动模式阻止`direct-flow-hard>16384`。本次仅在主程序冷配置准入以`split-enable && route-mode!=all`限制Direct资源cap，公共DNS/MTU/启动填充的其它错误继续拒绝；活动Direct仍保持1..16384。更新唯一受影响的原Go装配patch和精确计算`result_blob`（旧原Go派生blob预校验）而非偷换原donor。

同期原WinForms→原Go CLI fixture补验：旧CN缺键迁移true、显式false分别保存并重开；已启split但all、或split off而保存CN mode，若无活动规则且`direct-flow-hard=16385`，**read-only** `--check-config`应准入并保留请求值；活动CN仍必须因缺规则/超cap拒绝。实际Windows GUI/Go/Rust同源编译workflow因原fixture路径变更而触发，但本SOURCE结果**NOT_RUN**，本地GUI准入不等于Rust OS Applied。GUI原功能卡仅写待验，029B剩余B3真实IPv6发包、B4多代/Game、B5 <=10Mbps同VM A/B仍在。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback"],"reason":"H2104 original Go CLI inactive Direct cap admission and real WinForms/CLI saved old-key+explicit-false lifecycle test; original B0 signed source PASS scoped; GUI new SOURCE NOT_RUN"}
```
