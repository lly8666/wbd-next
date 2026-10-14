# M0 R0 LINK/FEC wire + MTU 旧Go oracle 的单原子施工计划

2026-10-14：恢复远端HEAD `19361ddd0da148e12df3877ada36621ca244d938`，cursor seq15/checkpoint `ca39ff2e52142da6a2082dc7bfa27b2fff1b0b6c` 后仅cursor-only H，Governance 38524046574成功，0 open PR，M0 main/epoch1/revision1唯一激活写者，CLEAN。读取00/06-LINK-MTU/07-FEC/11及原Go固定`lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`实际`internal/linkdata/datagram_fragment.go`、`internal/fec/fec.go`和`fastblock_encoder.go`。

**why_now**：R0先前锁定原Go TLS record密文外头与WBC4/WBG4，却没有把20B LINK fragment与56B FEC streaming/final头和MTU预算建立Rust可测试规范。并行worker不能各写自己不兼容的fragment/FEC wire。本轮只做真实旧Go witness + Rust wire/offset，无Rust FEC计算或真实重组。

**边界与fixture**：`r0/fixtures/legacy-link-fec-wire-v1.txt`含真实原Go算法静态预期：MTU64的LINK payload65拆成44+21，首/末片WBDLFRG1/version1/reserved0/index/count/total/packet_id；8B fragment magic必须escape；adaptive FEC-off的WF!必须escape，fixed off原样；FEC 20:4 的首个3B streaming source头（flags1,count20占位，只有自己的length3），最后k1 parity 56B头（flags0,count1,shard index20,配置parity仍4）。后者明确**只有头部**，parity payload来自实际原Go generator，不制作假的“FEC golden”。Rust仅对真实同fixture用显式BE字段，检查MTU±1、非法count/id/version、65535总长/越界、真实流式source和final geometry。完整L01还包括真实owner/重组资源/系统MSS，不标PASS。

**Actions**：同SOURCE Ubuntu 24.04 Linux amd64 pinned Go1.23.12/Rust1.85.1，固定旧Go repo只checkout/临时增加R0测试文件（不提交旧库），编译真实`internal/linkdata`/ `internal/fec`两组Go单测二进制与Rust codec测试二进制一次；单独consumer下载三原生二进制，确认精确SOURCE/run/attempt/compiler/fixture以及全部输入SHA256、binary bytes/hash并直接运行Rust7测试+Go LINK2/FEC2项。保留原record6组及WBC/G13项独立workflow，三组包及旧工具的source-input hashes覆盖新Rust module，避免未来旁路源码证明。

**done_when**：本task真实Actions与回归明确绿色，无加密/业务/FEC数学虚报，精确run+artifact+hash/evidence写入唯一R0 manifest，S证据与独立cursor-only H交接。发现失败仅据实际job日志修正确切反例。

**并行开发门槛**：本轮结束不自动激活M1–M4。由M0核共有 FrameBudget/record/codec依赖/worker接口与写权限清单，确定够分割R1 Normal/off、M3三cipher、M4平台驱动、M2恢复纯状态机后，单独一个有权限的registry派工动作；无需等R5/物理/性能全部验证，不能给未核对的日期。阶段R0 partial、生产Go V4 DISABLED不变。

**唯一下一动作（本轮绿后）**：审R0仍缺的 record真实AEAD/HP与FrameBudget所有权，判断是否可先正式激活独立worker的最小R1职责，先记录明确每人branch/allowed_paths/owner接口和G2影响，再开始并行；不因本轮静态wire测试直接开产品V4。