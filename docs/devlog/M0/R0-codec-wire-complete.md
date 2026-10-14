# R0 WBC4 receipt-control bundle + WBG4 Game envelope Rust wire codec — 完成收据

2026-10-14 M0。开工前刷新远端主线、project/registry、M0 cursor seq11、00/08/09/11模块与旧Actions，checkpoint `f5ae7ddf95363a61ca7d27d9157c049c16df7242` 到HEAD `6ff20b87395e64d3f0e403b188b97a331f1acda9` 只有一笔cursor-only H，最近run全部结束，0 PR；M0 main epoch1/rev1 active，判定CLEAN非产品PASS。

**why_now**：正式R1 worker前先锁WBC4/WBG4显式wire布局与非法输入失败关闭。08-RECOVERY显示receipt TLV type1不是泛化字串，而是固定20B字段加每页40B 256PN bitmap且最多8页；先消费这条既有契约，禁止发明另一套wire格式。

**substantive S**：`fdcacde4dae62cb6591d030d93ced7715b919118`，新增 `crates/wbd-codec` (只依赖wbd-types，Rust 1.85.1，无第三方crate)，及`r0-codec.yml`和`tools/r0_codec_bundle.py`。接口只处理调用者提供MTU payload预算的受保护V4 plaintext：`encode/decode_control`和`encode/decode_game`；没有 socket、认证、密钥、真实receipt handler或跨lane Game data engine。Rust struct从不直接dump入wire，所有 BE offset和长度明确组装/解析；legacy V3的9B health不由magic做fallback。

**golden**：手写固定 WBC4 receipt72B（largest258, ack_delay2500us, seq7, page base256, bitmap0x05）、WBC4 legacy TLV 21B、WBG4 ID 0x0102030405060708 + 0xDEADBE 19B。Rust 13项通过 golden roundtrip、schema/type/flags/长度/预算、8TLV、重复receipt、receipt 20+40×pages及page_count/256页base、未来PN位/u64::MAX/ack_delay上界、Game payload 0/65535与 u16长度/flags/截断。**本阶段是wire结构验证，不会凭bitmap承认业务数据已被远端认证或收达**，上游authenticated LaneKey/epoch归属和真实发送PN检查要后续engine/recovery做。

**Actions**：[38519636181](https://github.com/lly8666/wbd-next/actions/runs/38519636181) attempt1 exactSOURCE `fdcacde4dae62cb6591d030d93ced7715b919118` completed success，build job115706153296仅编译release wbd-codec和Rust test binary，consume job115706242766独立下载并检查源文件SHA256、SOURCE/run/attempt/compiler、二进制哈希后执行13/13测试，0失败。build artifact id11873081899 sha256 `643d1d6ef359ed1ba04b32a34b6caebbbd3c3e85a95420c809b38c2a3dd963cc` bytes472806；result artifact id11873086957 sha256 `704a43972f4cac11bc75548ccc7b450d8aabe145be1f1bdb98fc315a028e681b` bytes1391；原编译unit binary `3b26811fff9f691d44a47829f423ae0da83034efb267dd051ea7b7a331bcb2fc`，test log `1a0da9c1e3d5022f6df65d7ecb98d3d803916cfd06544ec75d23e35c3bd02468`。GitHub报告ZIP摘要，未独立下载archive；内部binary由consume独立核验。

**同SOURCE受影响回归**：Rust fake-platform run38519636182、types build run38519636189、Windows/ARM64 cross-only run38519636196、Governance run38519636197、Linux native Rust-C-pinned-Go ABI run38519636220全部success，独立jobs已核；跨目标依然不是Windows/ARM原生运行，旧Go原始仓库不写。

**限制**：R0总体仍`R0_FOUNDATION_IN_PROGRESS`、unverified；真实Rust AEAD/LINK/FEC/receipt/延迟首到、Game共享FEC、多lane数据面皆未完成，旧Go控制生产V4仍DISABLED/features=0。Windows/ARM native execution、完整产品/性能/物理NOT_RUN。M1–M4 reserved，不能将13/13 codec通过直接变为上线资格。

**本原子done_when**：WBC4/WBG4 wire codec实际Rust compiled+precompiled consumer成功、上下游workspace触发回归全绿、源码/哈希/未测范围可恢复，已满足并收口。

**唯一下一动作**：检查`r0/source-lock.json`历史bootstrap状态与新四crate workspace/各workflow真实test ID覆盖的偏差，形成单一可审核R0 foundation退出清单；先做证据审计和来源锁准确性修正，再讨论是否正式分派M1–M4，生产V4依旧禁用。
