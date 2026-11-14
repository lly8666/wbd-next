# PLAN029 H1816｜P2静态复用门禁首错、P1 WSL2原始SOURCE不继承的首错修复

- H1815 Action43572438752在 cheap `tests.test_delivery_ci::test_preflight_has_no_native_runtime_or_driver_effects` FAIL，16项其他测试PASS。旧单行expected不包含当前新`[plan029-v3-real-p2-mixed]`严格SOURCE/hash复用排除分支，导致**真正Windows驱动/WSL2业务未运行**。此提交按实际门禁精确更新测试及未来 P1 reuse flag 的严格包含断言，生产逻辑无修改。
- P1 H1814 Action43571086653 A腿真实Kernel两端 49.99/50Mbps、UDP/TCP与owned Stop PASS，协调器因 WSL2 -u root 原生 Linux rate-app 的`source:null`报首错，B停止。修为Windows应用必须 GITHUB_SHA，Linux应用只有null或相同SOURCE可以接受，**但 Linux server产品必须通过原始从Action43571086653精确SOURCE/hash/manifest恢复、report linux_binary_source等于Frozen SHA、两OS scenario hash和真正交付也必须通过**，不软化真实业务。
- 本H1816仅commit marker `[plan029-v3-real-p2-mixed]`，另一个 H1817 才commit P1 marker，运行在独立Windows Runner，不共用OS路由。两次都复用已存在的H1814 Windows Exe/DLL与 Linux Go/Rust server；P2/H1816和P1/H1817运行结果未收不宣称PASS。不同场景并行、同VM只顺序owned。
```feature-impact
{"kind":"none","ids":[],"reason":"Repair outdated exact static preflight condition and WSL2 guest environment source gate in tests; no product runtime/default/ABI change."}
```
