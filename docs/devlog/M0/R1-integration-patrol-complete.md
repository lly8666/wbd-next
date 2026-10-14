# M0 R1 Normal/FEC off 前置集成巡检 — 完成收据（2026-10-14）

开工读取远端main HEAD `694bfaae5ef03827e057726c73262b2110f5d5a2`，M0 cursor seq19 checkpoint `572de3c508a797124b12e3f32830ca43d1ffea5c`，checkpoint→HEAD只有cursor-only H，Governance38535803104 success、registry revision2 M0+四worker active，open PR0，历史run未完成数0，判CLEAN（非产品PASS）。

最初四work分支确实都停在旧SOURCE `0845e739...`、cursor seq0、无请求。但**巡检过程中**四方同时推送真实代码，必须废弃最初的“没有交付”的时间点推论。随后对各work refs、worker-native run/cursor/请求重新核实，证据快照和精确SHA全在`docs/evidence/M0/R1-integration-patrol.json`；不能推断四个聊天是否正在本地继续写代码。

**当前生产约束与M0独属阻断**：`wbd-engine/Cargo.toml`最初仅types依赖，无法集成codec/platform/recovery；`tools/r0_qualification_audit.py`还强制所有crate只能依赖types，阻断真实R1组合。M0实质SOURCE [93503a4](https://github.com/lly8666/wbd-next/commit/93503a4fc7d6bec305e20ae361cb5472905668d0) 只改M0持有的engine Cargo/lock、source-lock与静态审计，允许**仅engine**直连types、codec、platform、recovery，三下层仅types，types纯，锁仍零第三方依赖，CDylib features=0继续不暴露新产品资格。 `docs/devlog/M0/R1-normal-off-integration-ports.md`固定各worker第一个可消费输出、唯一buffer owner/真正AEAD+HP/只读driver/receipt独立、in-process真实业务单包同SOURCE验收，不以Cargo编译或Go golden冒充Rust Open/Delivery。

**SOURCE 93503a4精确Actions**：`g2-bootstrap`38538320148、`r0-qualification-audit`38538320136、`r0-native-abi`38538319960、`r0-cross-abi`38538320140（目标native执行仍NOT_RUN）、`r0-build`38538320080、`r0-codec`38538320025、`r0-record-framing`38538319977、`r0-link-fec-wire`38538320162、`r0-platform-fake`38538320035、`r0-go-control`38538320118、`r0-go-vectors`38538320092、`r0-v4-tls`38538320028、Governance38538320018全部**SUCCESS**。Go旧库未写入，产品/性能/物理NOT_RUN。

**本轮真实新公共CI阻断**：M2 SOURCE `7b02154...`的旧G2 consumer38538225378 FAIL：实际Rust 9/9 PASS，其中8项是M2新receipt状态，旧consumer仍要求“整个binary只有1项”，故是假阴性。M4 SOURCE `bcf0bca...`旧platform38538117164 FAIL：真实13/13 PASS（R0旧7 + R1新6，包含Linux UDP native smoke），旧consumer仍强制总数7；这与M4请求`.governance/workstreams/M4/requests/M4-M0-R0-platform-filter.md`一致。M0 followup SOURCE [40a8a53](https://github.com/lly8666/wbd-next/commit/40a8a53c8382d24b5f66fdf8e72d42d71a0ecc36) 不放宽断言，而是把旧G2限制`--exact tests::bootstrap_is_not_product_qualification`、旧platform限制`r0_`，继续严格验1/1和7/7。主线`g2-bootstrap` [38538899469](https://github.com/lly8666/wbd-next/actions/runs/38538899469) build115768504587/consume115768602368 SUCCESS，`r0-platform-fake` [38538899575](https://github.com/lly8666/wbd-next/actions/runs/38538899575) build115768505193/consume115768618150 SUCCESS，Governance38538899485 SUCCESS。**这只证明新main旧scope修正合格，不可倒改旧worker SOURCE失败结论，worker尚须自行正常接收M0主线修复。**

**四角色可用性快照**：
- M1 初始实质S `46571e69...` `worker-native`38538248506 原生10/10成功，提交真实owned buffer/arena+runtime局部队列/fresh优先。后续H `e511f133...` cursor seq2、unverified=false、progress ready_for_integration，Governance38539033023成功；早期两笔cursor H失败由M1独立修复，历史不抹除。真实wire seal/owner E2E未验证。M1请求`rtrb` +`loom`作为下一阶段SPSC/模型验证，记录为**已审接收、暂缓引入外部crate**：首批模型在无依赖范围可测试，版本/锁/许可/热路径归属需M0单独审查，避免影响当前Normal/off首包。
- M2 实质S `7b02154...` `worker-native`38538225302 原生8项receipt状态测试成功，后续H seq2、partial/unverified=true、Governance38539068727成功。M0只修历史G2计数；不合并不同源结果伪造已认证receipt业务路径。
- M3 最初SOURCE `44975170...`的`path_budget_tests.rs`缺少`LINK_HEADER`/`MAX_WIRE_LEN`导入，编译/old regression真实FAILED。M3随后SOURCE `3aa121e...`自修并验证`worker-native`38538473699、`r0-codec`38538473703、old LINK/FEC和record及Governance均success，但cursor仍seq0 checkpoint null，尚待worker完成自己的首笔S/H。不越权修改M3源码。
- M4 实质S `bcf0bca...` `worker-native`38538117103 6/6成功：5 fake/bounded/loan stop + Linux原生UDP smoke1，不是AF_PACKET/sendmmsg/Windows或产品性能资格。后续H seq2、partial/unverified=true、Governance38538965938成功，旧R0平台失败需M0新脚本经新来源重测；正式M4请求已被M0 main修复回应。

**并发安全**：M0没有push/force/update任何work refs，所有四方分支提交属于独立worker；本轮未合并它们的实现到main。全体当下历史10个R0 scope均限于各原始精准SOURCE，其绿灯加上worker分支测试**不能自动合成为真正R1业务收发**。Rust三cipher认证seal/open、real combined engine、R1 Normal/FEC-off业务payload端到端尚未交付，Go生产V4仍DISABLED。M2 receipt不挡Normal首包，M4热路径CPU和实际OS驱动后续测。

**本轮done_when**：核远端roles/branches/requests/runs、解决M0持有的根engine依赖方向和两旧Actions误报、观察实际native编译和旧源测试、将不同worker scope及请求处置/真正首包必要条件写明。已满足。下一唯一动作：在M3真实Rust加密接口+自持S/H与M1/M4集成就绪后，由M0将实际通过的worker模块版本安全合入单一main SOURCE，运行一个Rust业务input→Seal→Normal/off wire→真实Open认证→业务delivery 的完整native闭环；纯in-process与OS driver、Go生产升级和性能分开，不等R2/FEC阻塞首包。

**M0 H恢复事实**：第一次cursor-only H [`b79a140`](https://github.com/lly8666/wbd-next/commit/b79a1404ae08115dae4cae2b72eadac07cc178dc) 的 [Governance 38539971191](https://github.com/lly8666/wbd-next/actions/runs/38539971191) **FAILED** 于 validate_repo，因为M0的context_refs误包含仅存在worker分支的 M1/M4 request 文件；并非编译/协议失败。源码和前述通过的run不改名、不重记。纠正：worker requests仍在本JSON及日志里精确注明，但只把main确实有的文件留在M0 cursor context_refs；需新收据S和cursor-only H后再次验证。
