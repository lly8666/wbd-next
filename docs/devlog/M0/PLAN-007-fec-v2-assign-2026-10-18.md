# PLAN-007 · PR#10合并后重新安排已待命工位

2026-10-18审查最新PR#10，源HEAD `5c4797c2e2c76ea530e860df240b7b4b494c473e`、维护Action39078298503同源SUCCESS(171 tests及模型)、范围仅设计/模型/提示词，GitHub正常合入 main commit `365cbbcffdac5773a0a151a8c6b0dc5be5fb4f52`。旧中间Action39078188315的模型断言FAIL保留，最终修正有独立PASS，原生/真实数据面/物理仍NOT_RUN。

main注册前读到M1 HEAD `d91454c` seq16 ready Game013（CODE `e2050aec` 117/117）；M2 HEAD `9b70e35` seq25 ready recovery010（CODE `654a3c1` 70/70）；M3 HEAD `093e6f7` seq30 ready codec016（CODE `422a261` 113 default/native3+同机ABBA）；M4 HEAD `a48c53f` seq19 ready platform013（CODE `b7bcde7` 94/94）。M3最新H30中央形式审计39046275022 FAIL("verified cursor lacks reviewed PASS evidence")，早先H29核验通过；不改历史/不伪造PASS。

main已按差异阶段导入M1/M2/M3源码，M4原批量路径与main相同，无需再覆盖导入。旧源码 `fca4456313e59c0a67f4d8b98959a62d2af71b12` Normal/FEC-off基线/D10 run39032995995 FAIL保留；main源码 `ede83b98...`的真实Go TLS→Rust raw/TUN功能Action39047975684 PASS，但codec unified native-functional串行/4threads分别39047975666与39048697568均240s timeout退出124；P10 AB39048219356 B CPU+4.58%、BA39048219347 B CPU-1.46%不稳定且B-p99偏高，SPARSE39049004790 B p99 168→196/341→394us，全部留OPEN。真实FEC-on/Game多lane/repair反馈/超MTU自动fragment产品组合未验。

本次只登记新M1 `R5-M1-FEC2-OWNER-SCHEDULING-014`、M3 `R5-M3-FEC2-CODEC-NATIVE-017`、M4 `R5-M4-FEC2-COLD-POLICY-PLATFORMS-014` 三个独立完整工位包；保留相同worker分支和epoch，旧cursor照旧记录上一任务直到其恢复后自己H。M2已交付恢复010继续待命，M0主线原R0-023任务未被丢掉。为M4只追加新Go overlay两个确切文件与`native/isal-safe/build.rs`，其他真实Go/C ABI/配置/CLI/GUI/共享CI仍M0单一写入。公共接口/非产品资格边界见 `docs/decisions/M0-fec-v2-contract-freeze-2026-10-18.md`。

本轮无Rust/Go数据面产品变更。下一步：各工位根据新main registry以及自己cursor校验后连续做完整工作包，不需等待其他工位；M0继续真实Go接口、Stop/MTU及具体codec超时/延迟风险定位，先组合功能后性能；所有运行仍只在Actions；未满足组合硬门不打开产品开关。
