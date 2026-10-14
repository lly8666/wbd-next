# M0 R0 WBC4/WBG4 明确wire codec：施工边界

2026-10-14。远端main HEAD `6ff20b87395e64d3f0e403b188b97a331f1acda9`，cursor seq11 checkpoint `f5ae7ddf95363a61ca7d27d9157c049c16df7242` 至HEAD仅一个cursor H，Governance run38517944144 success，0 open PR，M0 main/epoch1/rev1 active，CLEAN不代表产品资格。

**why_now**：此前已锁Linux native Go↔C↔Rust ABI，以及Rust fake platform和Linux ARM64/Windows x64跨目标编译；然而00定义的V4 WBC4 bundle/WBG4 envelope 尚未有 Rust explicit-offset/golden，继续扩大引擎模块会因隐式布局/未知长度造成错包或业务误交付。按seq11唯一任务先做纯wire codec。

**授权/唯一语义**：新增无外部依赖 `wbd-codec`（只依赖纯 `wbd-types`），没有 socket、clock、AEAD、worker、线程、TLS或用户业务。仅解析由**上游完成认证并已协商V4**后的plaintext bytes；调用者提供有效record MTU payload预算，codec不能创建认证身份/借用原Go V3 health作为V4猜测fallback。

**WBC4**：严格按00的magic(4)、schema(1)、count(1)、total:u16(BE,含8B头)，至多8 TLV；每项type:u8、flags=0、len:u16(BE)、value。type1=receipt，其value遵08：20B固定字段(largest:u64/ack_delay_us:u32/report_seq:u32/page_count:u8/flags0/reserved0) + page_count*40B，最多8页，每页base:u64需256对齐+bitmap[32] little-bit ordering，base不可重复，任何置1 PN不能溢出或晚于largest；ack_delay<=10ms。type2/3仅保留legacy健康/质量opaque payload，不主动混用旧原始health；type1不得重复；未知type、flags或reserved非零、trailing、计数与长度不符、超过record预算全部拒绝。report_seq是否重放、未来未发送PN判断等**只能**由后续授权/关联发端状态的M2实际receipt handler决定，本codec不建立回执资格。

**WBG4**：magic(4) + LogicalPacketId:u64(BE) + payload_len:u16(BE) + flags:u16=0，总头16B；payload可为0B或65535B，必须精确匹配并受调用方预算；本codec不执行Game逻辑dedup、LINK/FEC排队，序列化严格显式offset、绝不Rust struct dump上网。

**golden/test**：源码内手写WBC4 receipt72B、legacy TLV21B、WBG4 19B独立固定向量；13组Rust测试覆盖两方向编码/解析一致性、长度从0截断、旧V3拒绝、schema/type/flags/count/overbudget、receipt 20+40n及page_count限制/未知重复/ack超时、PN未来位/256对齐/u64::MAX、不一致Game payload/零与65535边界。不是Python代数替代Rust。

**编译/消费**：Linux ubuntu24.04 x64 Rust1.85.1 Actions build仅编译release`wbd-codec`和预编译测试二进制并归档源码SHA256+runner/attempt/run id/binary size/hash；独立consume只核对再执行13组，不重新编译。workspace和Cargo.lock变更会触发既有受影响workflow的回归，全部事实分别按同SOURCE写收据。

**本原子done_when**：Actions原生Rust codec 13/13通过、二进制消费真实校验、旧workflow回归没有未查失败，记录SOURCE/run/artifact/hash/未覆盖、独立cursor H，R0整体仍partial。

**唯一下一动作**：审计R0退出合同、`r0/source-lock.json`历史快照与当前workspace/qualification实际差异及统一test ID→manifest覆盖，明确哪些基础项足以分派M1–M4、哪些仍阻断；先事实审计，不宣称R0完成或擅自激活生产V4。
