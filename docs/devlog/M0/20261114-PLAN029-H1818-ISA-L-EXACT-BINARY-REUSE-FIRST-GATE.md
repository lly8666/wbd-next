# PLAN029 H1818｜SOURCE锁定 native ISA-L artifact 与P1静态原文验证

- H1816 P2 [Action43572814169](https://github.com/lly8666/wbd-next/actions/runs/43572814169) cheap PASS、Windows/Linux不重复构建，但 Windows成品复用中断于 `assert m['features']=='m0_v4_embedded_go,fec2_product_record'`。原H1814 action43571086653确实构建了带 `native_fec_acceleration` 的 ISA-L release，不应误标成纯scalar；既有`sha256['exe']/['dll']` 与原Go捐赠SHA检查保留。新增**仅** run43571086653 + SOURCE `c262636c81d688e8df8e844b668bbcc57957425d` 双重校验分支，要求精确ISA-L feature、native_fec_acceleration=true、正确donor；仍逐文件校验hash和大小，其他未知features fail closed。
- H1817 P1 [Action43572971519](https://github.com/lly8666/wbd-next/actions/runs/43572971519) 在cheap static test失败：检查字符串漏掉实际 `len(b)>100000 and ` 前缀。已修为必须出现真实完整大小+SHA256表达式，并同时检查ISA-L专用入口。原来P1 A 50Mbps真Stop的证据不篡改，B仍NOT_RUN。
- 只改CI/static/cursor，不动数据面、默认配置、驱动或Linux编译产物。H1818只发 P2 marker，H1819用P1 marker单独Runner并行；如果真实网络首错后续独立追，不重跑无关纯单测或极端负载。

```feature-impact
{"kind":"none","ids":[],"reason":"Only recognize exactly verified H1814 ISA-L native feature set in SOURCE/hash-guarded binary reuse, correct literal static hash assertion; no compiled product change."}
```
