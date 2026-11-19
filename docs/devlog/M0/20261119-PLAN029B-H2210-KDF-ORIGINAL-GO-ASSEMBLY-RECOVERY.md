# H2210｜H2208遗留 Linux route-key 原Go装配缺项，H2209回落源锁恢复

2026-11-19 用户要求 M0 继续并在短Key任务后迁移老项目非WBD访问回落；H2209首次SOURCE `d7a34bbb567ac10a6f84dda77009e6c129e8a624` 已复用固定旧项目 original-Go P2 `FallbackFromHello`，Ubuntu Action [44427716175](https://github.com/lly8666/wbd-next/actions/runs/44427716175) 同源Go FakeTCP/TLS三场 **PASS_SCOPED**：普通访客错Key真TLS/HTTP应用数据、有效WBD零Decoy拨号、错SNI零拨号；不是实体公网端到端。

**首个失败**：多条 H2209 新SOURCE触发的旧 Linux x86/ARM native Action 如 [44427716410](https://github.com/lly8666/wbd-next/actions/runs/44427716410)、[44427716332](https://github.com/lly8666/wbd-next/actions/runs/44427716332)，在原Go编译时报 `internal/v4productcli/linux.go:41:5: no required module provides package .../internal/v4routekey`，因此这些Action **FAIL_BUILD** 不能归因为H2209 FakeTCP/Decoy、也不能声称新 Key 双端TLS验收。根因是 H2208 KDF 三文件原先只由Windows专用`prepare_windows_wiring.py`手工复制，原`manifest-plan020-m0.json`漏列；Linux native脚本经单一清单装配未得到此包。

本H2210按需仅修冻结source assembly：为 `internal/v4routekey/{short.go,short_test.go,cache.go}` 增加精确 `create` 与各原始Git blob；Windows assembler只验证**已经由相同manifest安装**的三件与冻结源码逐字节一致，不再二次复制/竞争owner。无新KDF、无Go热路径/TLS/客户端协议/Rust/FEC/外层wire变更。再次同SOURCE Linux/Windows装配及小范围真实原Go TLS/P2回落检验，失败不改旧证据；老029独立Windows Rust DNS Direct单元FAIL保留。

H2209尚未验：实体NIC、公网NAT/浏览器外网TLS、ARM跨机真实专用场景；旧专用Game2/4的decoy被明确拒绝，只默认shared安全支持Normal+Game2/4。H2208 Android仅私有设置helper，JNI尚未接通。

```feature-impact
{"kind":"none","ids":[],"reason":"Repair source-locked original Go assembly of already-implemented H2208 v4routekey package shared by Linux and Windows; no new product runtime semantics beyond H2209 code already recorded in previous changed feature card."}
```

## H2210 首个 Linux 独立单测失败与最小修正

在新增 exact-source 原Go Linux Go/Rust parser 验证 [Action 44429183683](https://github.com/lly8666/wbd-next/actions/runs/44429183683) 中，第一阶段已通过源锁装配，Go v2 KDF 8/16/32向量与拒绝输入通过；第3项缓存首写 **FAIL**：`route-key cache directory must be private (0700)`。这是 Go `testing.T.TempDir()` 在Linux实际可为`0755`，而产品真实缓存目录严格要求0700，之前 Windows 测试未触及POSIX目录权限边界。原 Go 测试夹具在首次`Resolve`前显式`os.Chmod(testDir,0700)`，**不改产品代码、不放松cache目录0700/密钥文件0600**；Linux实际产品Rust编译/CLI解析在这次 Action 还没跑，正确标识 NOT_RUN。重新按冻结 manifest hash 验，不能把原FAIL冒称通过。

## H2210 Linux parser 第二个失败与 H2209 标准普通访客夹具

[Action 44429623025](https://github.com/lly8666/wbd-next/actions/runs/44429623025) 在修复私有测试目录权限后，原Go短Key v2 3项已真正PASS；Rust源码编译也走到Go链接阶段，但`v4productcli`编译`undefined: realityfront.V4LinuxGameCohortID`等。首因不是业务接口缺失，而是本次新测试作业只调用`assemble.py`，漏掉**旧冻结Linux真实原生脚本**固定的`realityfront`、`v4productcli`附加Go bridge、`faketcp/raw_detached_data_linux.go`、原server cmd; 已按既有`m0-plan028-tls-wire-original-x86.yml`源锁复制规则在新工作流组装，严格对已有文件逐字节比较，不重新造业务类。

与此同时，H2209第一正例从“故意错RouteKey的WBD uTLS”替换为**标准Go `crypto/tls.Client` 普通非WBD TLS**，真实TLS1.3握手、SNI、ping/pong、close_notify、回放原始Hello；原WBD正确key、错SNI两场独立留存，避免以错Key客户端冒称浏览器验收。更新原V4 Go夹具与精确manifest，等待同SOURCE Ubuntu测试；公网实体仍NOT_RUN。新parser测试强制grep出现`TestH2209ServerDecoyColdValidation`与`TestH2206ServerNAT`真实PASS，不允许空匹配冒充验收。
