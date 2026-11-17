# PLAN029 H2016｜首个Rust E0277编译边界修复
- H2015原SOURCE `47a29b4c1d66583112611bd21f3a6f5df9893249` [Native Action43887327387](https://github.com/lly8666/wbd-next/actions/runs/43887327387) Windows/Linux Rust FAIL，bool `candidate()`保留3个`?`，而旧组件测试还引用不再存在的`startup_padding.len()`且错误限制为2KiB；均在真实网络之前，NOT_RUN不可升格。
- 三个u16字段改成长度已预检的2字节读取，组件单测改成256次允许总填充>2048、不要求flow map，默认off仍为0。真实抓包/双Stop尚未实测。
```feature-impact
{"kind":"none","ids":[],"reason":"H2016 narrow compiler and old-test corrections after intentional removal of flow padding budgets."}
```
