# R0 source-lock / 44-case 证据对账完成（M0）
2026-10-14。开工前远端HEAD 1d773acfe7d17227486554b339350ee5228b183b，seq12 checkpoint 29ad2aa37874df0fb44ec08efb5274f1b0145265 后仅cursor H，旧run均完成、0 PR、M0 epoch1/revision1 active，CLEAN不等于R0 PASS。

**why_now**：旧 r0/source-lock.json 长期写 types-only、compiled=false、Go vectors/ABI NOT_RUN，已与真实四crate和多个Actions结果冲突，不能据历史引导锁凭空激活worker。源码S [c66416c](https://github.com/lly8666/wbd-next/commit/c66416c837108a2538394a446f3b91a18fd213e6) 使锁定源/工具链保持不变，更新为四crate及严格范围资格，并创建单一 r0/qualification-manifest.json 与 tools/r0_qualification_audit.py。

**验收矩阵**：唯一manifest载有8项历史证据的SOURCE/run/attempt、测试锚点、证据路径；00/11的44个ID中B01/R01/I01/C01只有fake子情境部分覆盖，其他40个NOT_RUN，没有任何完整ID凭治理文档标PASS；R0 exit状态仍BLOCKED_NOT_QUALIFIED。Rust engine功能位仍0、Go V4生产仍fail-closed，M1–M4 reserved。

**首次S实际运行**：静态审计 [38521076297](https://github.com/lly8666/wbd-next/actions/runs/38521076297) job115710658952 success，原生/Go 7个独立workflow通过：codec38521076328、Go control38521076319、platform38521076295、Rust types38521076283、Go-C-Rust native ABI38521076275、Go vectors38521076265、Go V4 TLS38521076264；治理38521076251 success。每组属于精确SOURCE c66416c、各自build/consumer，不能跨job当产品性能比较。

**新增发现与修复**：cross ABI源码读取source-lock并将其SHA写manifest，但是workflow push paths漏列该文件，因此第一次S未触发Windows/ARM cross，绝不虚构结果。第二实质S [35d599b](https://github.com/lly8666/wbd-next/commit/35d599b288ea19c3cead36b22ec561e4820ef38e) 将source-lock纳入 cross触发，审计增加8个workflow均必须随source-lock修改触发的断言。新SOURCE的静态审计 [38521306796](https://github.com/lly8666/wbd-next/actions/runs/38521306796) job115711382002 success，治理38521306875 success，跨目标 [38521307048](https://github.com/lly8666/wbd-next/actions/runs/38521307048) 2x build + 2x consume全部success；Linux ARM64仅cross-build（jobs115711383762/115711602507）与Windows x64仅cross-build（115711383944/115711602535），没有实际执行目标系统程序。产物SHA与每个exact run见 docs/evidence/M0/R0-foundation-audit.json。

**边界**：新静态审计既不调用Go/C/Rust生产代码，也不联网实时确认旧run；历史run状态先经GitHub工具独立核对。M0仍只做R0基础/治理而非产品完成。真实Rust record三cipher AEAD/HP及旧Go wire golden、LINK/FEC/MTU wire、完整Rust引擎+OS I/O、业务V4 epoch/lease、Windows ARM原生执行全未资格化，产品/性能/物理NOT_RUN。

**done_when**：source-lock同步、44case统一锚点、旧回归绿、cross漏触发修正并双目标复用验证、准确证据落库、cursor-only H。不继续增加新的治理层。

**唯一next_action**：转回实际基础编解码，围绕00/05锁原Go记录格式，对Rust record外帧长度/offset以真实oracle做golden与失败拒绝，用Actions真实编译/消费，明确无AEAD实现不得伪造成功开密/业务输入。
**H恢复记录（不可抹除）**：第一次cursor-only H `b9bb7aef5a76ec8fff0085297744b5a7de64dad1` 对应Governance [38521896495](https://github.com/lly8666/wbd-next/actions/runs/38521896495) FAILED于 `Validate repository contracts`。确定根因：本次新建的 evidence JSON 缺少必要字段 `source_sha`，虽然已有测试精确SOURCE在 `code_shas` 和 `source_two.sha`，但治理校验要求 `evidence.source_sha == cursor.last_tested_source`，包括unverified cursor。因此本恢复提交补 `source_sha=35d599b...`、保留失败run并在后续独立H重新确认；原始失败与修复不会虚报为连续全绿。
