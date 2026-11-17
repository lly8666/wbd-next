# PLAN029B H2086｜按各自函数修复两条CI断言，恢复新SOURCE原生通道

现行 `SOURCE=1a9459285cbeab48e6db5f40953a9789cedf1b99` Action [44050649777](https://github.com/lly8666/wbd-next/actions/runs/44050649777) 的廉价范围门单测 FAIL：`test_h1859_p1_and_p2_bulk_both_build_exact_v3_before_native` 因H2085编辑时错误替换文件内第一处`getattr`断言，引用仅H1843局部的`abi_section`造成NameError；真正`test_h1843_real_product_v3_abi_built_and_checked_before_driver`的导出表达式保留多余反斜杠，导致AssertionError。H2086按**函数局部**编辑，分别校验 P1/P2老场景确实共享新默认release V3 feature、实际release PE export检查确实无条件且早于driver，且预读现行workflow做精确字符串一致性断言。

H2085其他同源实际已得到：governance `44050649785` PASS、静态`44050649812` PASS、native ABI`44050649718` PASS、cross ABI`44050649746` PASS、native-functional`44050650335` PASS、Win/Linux Rust Direct pressure`44050649813` PASS。真实Windows2025↔WSL2因为cheap gate FAILED而没有执行，B0–B5不得声称PASS；H2083 `44045024679` 的无V3导出真实FAIL与原H2077不同源码PASS均保留。

本批**仅两条CI测试断言+治理及留证**，绝不更改实际 Rust/Go/FEC/TLS/OS/Stop，不为测试重新启用旧管线或跳过安全门。

```feature-impact
{"kind":"none","ids":[],"reason":"H2086 only source-lock CI test assertion corrections and M0 cursor; no production features or feature-card semantics changed"}
```
