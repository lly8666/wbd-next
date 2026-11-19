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

## H2210 最终同SOURCE限定编译与测试

SOURCE `574cf32b2227fd9f0d8608a94764fe3f6011ad42` [Action44430144025](https://github.com/lly8666/wbd-next/actions/runs/44430144025) 二作业均SUCCESS。真实Linux主机编译本SOURCE Rust `wbd-engine` 并与原Go `wbd-v4-server` 动态链接，普通`--decoy`冷配置正反例、H2206 NAT单网卡唯一IPv4、H2208 v2短Key 3项真实POSIX目录0600/0700缓存测试均 **PASS_SCOPED**。同SOURCE [Action44430143721](https://github.com/lly8666/wbd-next/actions/runs/44430143721) cheap装配、Win Go/Linux Rust/Win Rust相应job PASS。历史Linux H2210第一FAIL因测试目录0755，第二FAIL因新测试漏装原Go bridge，均原始失败留存；未声称x86/ARM真实NIC业务或公网回落已验证。

H2211 ARM64旧手工Go bundle [Action44430144037](https://github.com/lly8666/wbd-next/actions/runs/44430144037) 的首FAIL仍是缺`v4routekey`，该脚本未用主manifest直接装配。仅在`tools/arm64_public_go_rust_bundle.sh`增同manifest验证3 Go文件，SOURCE `21acc95b5469e72872096f52702d1b62e128a25e` 的 [Action44430856253](https://github.com/lly8666/wbd-next/actions/runs/44430856253) 在写日志时未结束，后续以自己的SOURCE标记PASS/FAIL，不跨源搬用。

## H2211 ARM64 build-only 结论

SOURCE `21acc95b5469e72872096f52702d1b62e128a25e`：[Action44430856253](https://github.com/lly8666/wbd-next/actions/runs/44430856253) **SUCCESS (BUILD_PASS only)**。从同一冻结manifest读取并校验`internal/v4routekey/{short.go,short_test.go,cache.go}` Git blob，ARM64原Go双端CLI真实构建与Rust ISA-L加速`libwbd_engine.so`真实编译，Rust定向24/24+7/7；生成原有`manifest.json`/`SHA256SUMS`，不假称Android JNI/OpenWrt物理产品联网。旧SOURCE `574cf32b2227fd9f0d8608a94764fe3f6011ad42` [Action44430144037](https://github.com/lly8666/wbd-next/actions/runs/44430144037) 编译缺包FAIL历史仍保留。详见同SOURCE [H2211证据](../../evidence/M0/PLAN029B-H2211-ARM64-GO-RUST-ROUTEKEY-MANIFEST-BUILD-PASS-20261119.json)。

## H2212 只修治理热预算，不重算源码产品验收

H2209/H2210/H2211证据和cursor首次同批 [Action44431729729](https://github.com/lly8666/wbd-next/actions/runs/44431729729) **FAIL_GOVERNANCE**：`START_HERE`及M0 cursor扩张使原hot-read总量约33920B，大于固定32768B；这是治理结构失败，非Go/Rust/TLS回归。下一批仅压缩热入口重复历史段及cursor摘要（完整原H2205/H2208/H2209/H2210/H2211证据、SOURCE/旧FAIL保持冷devlog和evidence），热总量约32149B，不更改产品/测试或旧验收结论；按新SOURCE重新治理，不复用旧FAIL为PASS。
