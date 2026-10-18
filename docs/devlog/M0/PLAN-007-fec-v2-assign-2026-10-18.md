# PLAN-007 · PR#10合并后重新安排已待命工位

2026-10-18审查最新PR#10，源HEAD `5c4797c2e2c76ea530e860df240b7b4b494c473e`、维护Action39078298503同源SUCCESS(171 tests及模型)、范围仅设计/模型/提示词，GitHub正常合入 main commit `365cbbcffdac5773a0a151a8c6b0dc5be5fb4f52`。旧中间Action39078188315的模型断言FAIL保留，最终修正有独立PASS，原生/真实数据面/物理仍NOT_RUN。

main注册前读到M1 HEAD `d91454c` seq16 ready Game013（CODE `e2050aec` 117/117）；M2 HEAD `9b70e35` seq25 ready recovery010（CODE `654a3c1` 70/70）；M3 HEAD `093e6f7` seq30 ready codec016（CODE `422a261` 113 default/native3+同机ABBA）；M4 HEAD `a48c53f` seq19 ready platform013（CODE `b7bcde7` 94/94）。M3最新H30中央形式审计39046275022 FAIL("verified cursor lacks reviewed PASS evidence")，早先H29核验通过；不改历史/不伪造PASS。

main已按差异阶段导入M1/M2/M3源码，M4原批量路径与main相同，无需再覆盖导入。旧源码 `fca4456313e59c0a67f4d8b98959a62d2af71b12` Normal/FEC-off基线/D10 run39032995995 FAIL保留；main源码 `ede83b98...`的真实Go TLS→Rust raw/TUN功能Action39047975684 PASS，但codec unified native-functional串行/4threads分别39047975666与39048697568均240s timeout退出124；P10 AB39048219356 B CPU+4.58%、BA39048219347 B CPU-1.46%不稳定且B-p99偏高，SPARSE39049004790 B p99 168→196/341→394us，全部留OPEN。真实FEC-on/Game多lane/repair反馈/超MTU自动fragment产品组合未验。

本次只登记新M1 `R5-M1-FEC2-OWNER-SCHEDULING-014`、M3 `R5-M3-FEC2-CODEC-NATIVE-017`、M4 `R5-M4-FEC2-COLD-POLICY-PLATFORMS-014` 三个独立完整工位包；保留相同worker分支和epoch，旧cursor照旧记录上一任务直到其恢复后自己H。M2已交付恢复010继续待命，M0主线原R0-023任务未被丢掉。为M4只追加新Go overlay两个确切文件与`native/isal-safe/build.rs`，其他真实Go/C ABI/配置/CLI/GUI/共享CI仍M0单一写入。公共接口/非产品资格边界见 `docs/decisions/M0-fec-v2-contract-freeze-2026-10-18.md`。

本轮无Rust/Go数据面产品变更。下一步：各工位根据新main registry以及自己cursor校验后连续做完整工作包，不需等待其他工位；M0继续真实Go接口、Stop/MTU及具体codec超时/延迟风险定位，先组合功能后性能；所有运行仍只在Actions；未满足组合硬门不打开产品开关。

## 2026-10-18 · Worker状态纠错和M0共享Actions入口

- M1 CODE3f78a67 130/130 native scoped组件通过，但最新中央作用域39083333199明确`HTTP403 github_rate_limited remaining=0 attempts=3`，不是64提交上限；旧worker Governance39082738365本地checker的64上限是**另一故障**，均不作中央scope PASS。M3 H33 partial/unverified CODE301 scalar/wire通过；H30 39046275022非PASS仍FAIL，后续HTTP403保留补充证据。新的 M3 独立S scope39083652143成功只能证明该pre-H SOURCE的作用域，不能升017整包或产品PASS。
- M4 CODE7cef7e已有两个Go overlay和target build.rs。M0源锁Go original clone`a7a82db`+ M4 SOURCE`7cef7e8`工作流 `.github/workflows/m0-fec2-go-cold-policy.yml`，Action39084384517 SUCCESS build+consume；Go 1.23.12先编译一次真实realityfront，再校验哈希运行8个TestF2Control PASS。只证明冷策略Go包，未接live Go V4配置/GUI/应用回执。
- M0 平台Action39084579161 使用 M4 build.rs + ISA-L v2.31.1 pinned，Linux x86_64/ARM64原生均2/2 safe-wrapper TEST PASS并实际调用`ec_encode_data`；Windows失败，`nasm`命令未找到，属于nmake依赖缺失。只修Windows工作流添加NASM及PATH后，Windows-only39084759926 SUCCESS 2/2真实Win64 MSVC ISA-L safe-wrapper；Linux同次跳过，保留前次正确结果。真实ARM NEON指令级派发、完整M3 FEC2 native、Go Windows loader仍NOT_RUN。
- 唯一详细证据：`docs/evidence/M0/M0-FEC2-shared-workflows-4c1aa7c7dd9d0dba6a91a8c07d261dff4ec1f14f.json`，含精确run/attempt/job/控制SOURCE及GitHub报告的ZIP digest。**ZIP未下载复核，不自称artifact_zip_rehash_verified**，M4仍须按自己要求校核产物再更新worker的last_tested_source。保留所有旧失败和FEC2产品OFF；M0下一步按M3共享native请求做FEC2实际codec证据、按M4请求完成Go应用/GUI配置与原R0-023安全门，不重复老024性能调优。
