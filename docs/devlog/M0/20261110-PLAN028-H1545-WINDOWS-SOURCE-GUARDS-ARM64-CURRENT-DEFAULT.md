# PLAN028 H1545｜最新 main x86/ARM64/Linux/Windows 修复默认装配全覆盖核对

以 [`304ca72bac7dfa08b94e9fbc28f40e27fc61b928`](https://github.com/lly8666/wbd-next/commit/304ca72bac7dfa08b94e9fbc28f40e27fc61b928)、2026-11-08～11-10近期变更、原Go a7a82源树、现役Windows canonical manifest-plan020、Linux x86和ARM默认产物链为源。

**Linux x86：** 已用统一源锁11条Go FakeTCP，把H1285正确的64/65条原生TLS→M4接管放进真实编译；H1540实测30%/200ms/303.015Mbps、Game4热轮换5次服务端M4全部成功、六Stop均有；Carol Game2此前 stale49336+new57256 误混而真实双向断流，不能归为PASS。最新 `game_linux.go` 以原始认证epoch+原始client/server五元组+连续lane源端口作为同代分组约束，Game2旧/新防混单元 PASS；H1544修正Game4合法65535最后lane边界**测试误报**，产品未改。只需要新SOURCE loss30一场600s原生验证，已过0% 333.930不重做。

**ARM64 Linux：** 原 `tools/arm64_public_go_rust_bundle.sh` 已统一x86全套Go当前文件/11源锁。新增 `m0-plan028-h1546-arm64-current-default-bundle.yml` 在真正 `ubuntu-24.04-arm` 上使用当前 `github.sha` 构建原Go client/server+本次Rust/ISA-L，强制Go单测/ELF183/hash/来源源锁；这是**构建-only**，业务/物理内核收件和Stop仍NOT_RUN。现存 `m0-plan028-arm64-native-frozen.yml`固定140a旧源及旧Artifact，仅用于历史复核；决不偷偷把旧源BINARY当最新ARM64产品。

**Windows x86_64：** canonical manifest-plan020 **112** 原Go源锁操作，加受控 EXTRA 原17个；源代码逐文件对照发现7个新旧关键Windows测试源码未加入现役默认构建（真双Wintun OS隔离、H1381双账号owner、private Rust M4 guard、created Wintun以及原 Go TLS Game/FEC2三类），虽产品GO/Rust编译已PASS，但测试缺席。已在 `tools/prepare_windows_wiring.py` 受控源SHA守护表补至23 extra、1 CLI；Windows每次Go预检新增**编译** `windowsownerlease.test.exe`、`windowsclient.test.exe`，并真实执行不触网的两账号OS event测试；实际签名驱动/WFP的测试不在普通预检自动运行。严格排除 `plan020_local_mss_windows_test.go`：该test init会强制修改进程全局MSS1420，非安全产品默认；`ci/native_admin_preroute_real_crash_windows_test.go`独立非Go装配fixture。`tests/test_m0_plan028_default_assembly.py`要求**当前94个Windows overlay源码**全部由canonical manifest+受控 extras 覆盖（除上述危险init测试）。
已有 [H1544两OS构建](https://github.com/lly8666/wbd-next/actions/runs/42810065262) Windows Go/Rust和Linux Go/Rust/默认source审计 **PASS**，但五同机Wintun物理 /32 /1 route+WFP独立owner真实失败未修，必须保留第三方路由/设备WAL fail-closed，不可宣称五Windows READY或默认绕过。

**每次默认核验：** 主线Windows Go/Rust/assembly静态门、即将触发的H1541原生loss30和本次H1546当前ARM64 build均以头SHA为权威，不重派已完成历史场。全PLAN028依然IN_PROGRESS。证据结构允许PASS_SCOPED只指真实已完成部分。

```feature-impact
{"kind":"none","ids":[],"reason":"This checkpoint wires already-present Windows test-only sources into source-pinned Go test compile and adds current ARM64 build-only provenance checks; does not change shipping runtime options, security authorization, data plane or default user feature semantics."}
```
