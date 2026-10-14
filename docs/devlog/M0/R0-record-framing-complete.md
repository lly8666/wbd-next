# R0 固定旧Go真实tlsrecord密文见证与Rust opaque record结构 — 完成收据

2026-10-14；开工前读取远端main、project/registry/cursor seq14、00/05/11及旧Go固定`lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984` 的`internal/tlsrecord/record.go`、`decoder.go`、`vector_test.go`，checkpoint `e8b8125022333cb9818e734973da8ec179400f95`到HEAD `d173aa02ad8eae82b8fab723eb01ab044dd3eac4`仅一个cursor-only H，Governance38522202227 success，0 PR，M0 active/main/epoch1/rev1，CLEAN。

**why_now**：00/05规定复用老Go TLS-like record的受保护外帧，R0现有codec只会WBC4/WBG4，没有对应record framing。根据固定旧Go实码：outer五字节`17 03 03 body_len:u16BE`、8B protectedPN、密文（含加密kind+payload+0x17+零padding）及16B AEAD tag，最小body26/总31，最大body16640/总16645。HP取密文前16字节，在极短帧可覆盖认证tag。PN被独立HP掩码、kind在AEAD明文第0字节，**都不能由Rust外帧模块未认证读取**。

**单原子SOURCE**：[`e2fa27f2a912da60155f7fffceaab906fb52abe0`](https://github.com/lly8666/wbd-next/commit/e2fa27f2a912da60155f7fffceaab906fb52abe0)，固定原`internal/tlsrecord/vector_test.go`中真实独立六条完整密文黄金向量`r0/fixtures/legacy-record-wire-v1.txt`：pn0 empty、pn1 hello、pn(2^32+1)、PN MAX-1、PN MAX、pn7 payload含零/9B padding。Rust `wbd-codec::record_frame`仅`split_one`返回只借用的opaque record/剩余slice与`outer_header_for_body`，验证真实offset/length/MTU/短记录HP sample/不盲扫不可信length。该API不Seal、不open、不去HP、不识别明文kind、更不交业务。测试`r0/go_overlay/internal/tlsrecord/r0_record_wire_oracle_test.go`在Actions临时原Go树运行`tlsrecord.sealRecord`和`Opener.OpenRecord`实际ChaCha20Poly1305+HP，逐字节对照同份fixture且检查解密后的PN/kind/payload，并用`Decoder.OpenPayload`检验坏length不做magic扫描；旧远端Go仓库没有写入。

**真实Actions**：[run38523394776](https://github.com/lly8666/wbd-next/actions/runs/38523394776) attempt1 Linux x64，build job115718053277编译Rust1.85.1和固定Go1.23.12两份二进制一次；consume job115718227079在新job下载、校验本SOURCE/run/attempt/旧Go SHA、所有相关输入SHA256和两份test binary bytes/SHA256，执行Rust结构6/6 PASS、真实原Go 2/2顶层 PASS（其Seal/Open测试有6条子例）。未在consumer重新编译。buildZIP artifact id11874747579 digest sha256:b7e4503b9a12d55c41e9a0d552a1daca16c46336ed822804f9e119d63b8a9ecc，result id11875091493 digest sha256:f810adf402c49067c21070c0d69fd57b72150432983688821abd2077914af01a，Rust测试二进制SHA256 c746f376949fb2069239326f30f6fe13bd78fac2e190fc322dc99a6f1d7daf72，Go二进制SHA256 8db80d82bbd31c1a06090e6a3af5d62aa27cc09b553f349c80925a4aae3bf81f。GitHub ZIP摘要并非独立下载zip二次复核，consumer只验证内部二进制。

**独立回归**：同SOURCE原WBC4/WBG4 codec工作流run38523394984成功（其consumer显式skip六条record test，仍旧13/13），R0 source资格静态审计38523394792和Governance38523394740成功。修改`r0/qualification-manifest.json`的同一唯一8→9历史gate列表，增加本项真实Go和Rust证据，同时`tools/r0_qualification_audit.py`审核fixture 6条、Go/Rust测试名和禁止宣称Rust AEAD；44测试ID不因该子项升级为完整PASS，B01/R01/I01/C01仍是部分fake覆盖，其余40项NOT_RUN。Manifest更新属于证据声明，不可自动变产品资格。

**边界**：Rust自己的三cipher AEAD/HP仍NOT_IMPLEMENTED，真实Rust authenticated PN/kind/record payload未形成，Go应用生产V4继续FAIL_CLOSED，业务record data plane、LINK/FEC wire、Windows/ARM native执行、产品/性能/物理皆NOT_RUN。R0 partial，M1–M4 reserved。原源码测试不等于Rust已经有同等加密能力。

**done_when**：真实原Go加密wire six fixtures和Rust opaque parsing分别被Actions编译消费验证，并形成单一可回溯质量manifest与精确证据，已满足该scope。

**唯一next_action**：按00/06/07锁原Go实际LINK/FEC外头与MTU切分兼容oracle，提供Rust纯wire显式offset/长度边界、特别L01 MTU±1/zero edge与原Go黄金向量Actions预编译消费；不把假FEC当真实编码，不启用产品V4，也不自动激活worker。
