# PLAN029B H2080｜修复H2079真实首轮CI边界，不删旧FAIL

[H2079 commit `0b2d6b03bb7cce05e823e8620eb4312d878588d5`](https://github.com/lly8666/wbd-next/commit/0b2d6b03bb7cce05e823e8620eb4312d878588d5) 当前真Action：Windows编译/原Go装配等因 active `manifest-plan020-m0.json` 6份已改overlay source的`result_blob`未同步而 **FAIL**（原装配精确校验正确拒绝）；跨ABI/GUI因新Rust AAAA本地测试`let ... else`后缺一分号 **FAIL**；governance因cursor context_refs重复 **FAIL**，feature catalog check自身PASS。H2079仍NOT_RUN真029B业务，不删原日志。

H2080只修源SHA、测试Rust语法和cursor引用去重，保留新Go/Rust产物语义、cold ABI和旧H2077 signed Normal真证据，不改安全门或绕过装配检查。重收当前新SOURCE编译后继续收产品B0–B5，未验证不写PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"H2080 only source assembly result_sha metadata, missing Rust test semicolon and governance cursor references; no product feature behavior changed"}
```
