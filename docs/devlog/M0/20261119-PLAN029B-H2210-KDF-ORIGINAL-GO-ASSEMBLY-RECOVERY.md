# H2210｜H2208遗留 Linux route-key 原Go装配缺项，H2209回落源锁恢复

2026-11-19 用户要求 M0 继续并在短Key任务后迁移老项目非WBD访问回落；H2209首次SOURCE `d7a34bbb567ac10a6f84dda77009e6c129e8a624` 已复用固定旧项目 original-Go P2 `FallbackFromHello`，Ubuntu Action [44427716175](https://github.com/lly8666/wbd-next/actions/runs/44427716175) 同源Go FakeTCP/TLS三场 **PASS_SCOPED**：普通访客错Key真TLS/HTTP应用数据、有效WBD零Decoy拨号、错SNI零拨号；不是实体公网端到端。

**首个失败**：多条 H2209 新SOURCE触发的旧 Linux x86/ARM native Action 如 [44427716410](https://github.com/lly8666/wbd-next/actions/runs/44427716410)、[44427716332](https://github.com/lly8666/wbd-next/actions/runs/44427716332)，在原Go编译时报 `internal/v4productcli/linux.go:41:5: no required module provides package .../internal/v4routekey`，因此这些Action **FAIL_BUILD** 不能归因为H2209 FakeTCP/Decoy、也不能声称新 Key 双端TLS验收。根因是 H2208 KDF 三文件原先只由Windows专用`prepare_windows_wiring.py`手工复制，原`manifest-plan020-m0.json`漏列；Linux native脚本经单一清单装配未得到此包。

本H2210按需仅修冻结source assembly：为 `internal/v4routekey/{short.go,short_test.go,cache.go}` 增加精确 `create` 与各原始Git blob；Windows assembler只验证**已经由相同manifest安装**的三件与冻结源码逐字节一致，不再二次复制/竞争owner。无新KDF、无Go热路径/TLS/客户端协议/Rust/FEC/外层wire变更。再次同SOURCE Linux/Windows装配及小范围真实原Go TLS/P2回落检验，失败不改旧证据；老029独立Windows Rust DNS Direct单元FAIL保留。

H2209尚未验：实体NIC、公网NAT/浏览器外网TLS、ARM跨机真实专用场景；旧专用Game2/4的decoy被明确拒绝，只默认shared安全支持Normal+Game2/4。H2208 Android仅私有设置helper，JNI尚未接通。

```feature-impact
{"kind":"none","ids":[],"reason":"Repair source-locked original Go assembly of already-implemented H2208 v4routekey package shared by Linux and Windows; no new product runtime semantics beyond H2209 code already recorded in previous changed feature card."}
```
