# PLAN029 H2020｜Game4 CN验收夹具仅修场景变量初始化和旧检查
- H2019 [治理Feature Action43892285709](https://github.com/lly8666/wbd-next/actions/runs/43892285709) 仅旧H1934静态检查匹配`if p029_direct or p029_p1_policy:`失败。真实Game4新增第三支`p029_game4_cn`保留旧两个入口及其原UT，更新H1934两处断言。
- 同时审到H2017 Game4场景标记开头就验证`p029_p2/cache/pressure`，这些变量尚未初始化。将场景排他验证移到所有flag加载后，避免实际Game4刚进入夹具时`NameError`。不改Go/Rust产品、四lane/OS WAL或原检验门，保留已失败Action/NOT_RUN。
```feature-impact
{"kind":"none","ids":[],"reason":"H2020 fixes only Game4 CN fixture flag initialization order and stale H1934 static guard strings; product wiring unchanged."}
```
