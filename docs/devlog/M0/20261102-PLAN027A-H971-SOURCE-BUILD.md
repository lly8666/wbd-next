# PLAN027A H971｜避免重复SHA表之后补齐真实构建入口与NUL字节修正

H970 installer指向现行plan020原Go装配唯一七行表；检查时发现Python Git blob NUL拼写误写成两反斜线，必须用真实零字节`b"\\0"`才能和Git Blob一致。H970仅改installer非workflow监听列表，未启动产品编译。H971原子修复一处字符，并在已有Windows/Linux主Actions里添加installer本身和单测为push来源，同时执行廉价SHA全7行校验；对应ARM64注释不再称生产有固定1360 fallback。触发本次唯一必要源码构建和完整已认证驱动基线，既有H968/H969 FAIL保留，Native新源NOT_RUN直到Actions完成。原Go pinned不可变、Go/Rust生产MSS无新增兼容代码。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct one Git SHA NUL byte literal in source-exact installer; source-trigger and cheap test only, no product or configuration semantic change."}
```
