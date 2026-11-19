# H2150｜历史 H1749/H1934 源级断言跟随新的 Game 选择器

原[Action44225411753](https://github.com/lly8666/wbd-next/actions/runs/44225411753) 原生 **NOT_RUN**，首错是两处旧测试仍要求 `if p029_direct or p029_p1_cn or p029_game4_cn:`。新H2144真实Game2/4模式参数的目标是保留老Game4的确切CN选项，**排除新的 `p029b_game_case` 已配置冷策略的重复CLI参数**。只将两处断言与现存代码 `if p029_direct or p029_p1_cn or (p029_game4_cn and not p029b_game_case):` 同步；仍要求原True Direct、4096CN别名、旧H1749/1934真源锁验收的其他条件。没有产品Go/Rust变化、没有把旧Native PASS借给Game2。等此纯测试的治理PASS后才单独触发一次Game2签名网络。

```feature-impact
{"kind":"none","ids":[],"reason":"Only synchronize two historical source-string tests with the new Game2/4 signed scenario selector; no product or feature semantics modified."}
```
