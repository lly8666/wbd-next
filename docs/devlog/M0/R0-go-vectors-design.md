# R0-CONTRACT-001 / Go V3–V4 向量原子子任务

**why_now**：M0 seq5 的唯一 next_action 是在 Actions 真正编译旧 Go 的 V3 wire，并核验 V4 24B admission golden。此步是后续公共 Go↔Rust ABI 前置；不重新选架构。

**固定来源**：
- 新仓库本次 S 的精确 SHA 以 push 事件 checkout 记录。
- 旧仓库 `lly8666/wobuzhidao` 固定于 `a7a82db31fe736ffedee330795a3234d358f1984`；旧 `go.mod`：go1.23.1、toolchain go1.23.12。
- Actions 构建 job checkout 精确旧 SHA、setup-go 1.23.12、把仓内只用于测试的 `r0/legacy_v3_v4_probe_test.go` 加入旧 `internal/realityfront` 包；`go test -c` 只编译一次。consumer job 验 SOURCE、输入 SHA-256、二进制字节长度及 SHA-256 后运行预编译二进制，不重新编译。

**五组测试目标**（只有真实运行之后才记 PASS）：1. 原 Go `marshalAdmissionRequest` / `readAdmissionRequest` + `marshalAdmissionReply` / `readAdmissionReply` 对人工固定的 V3 字节；2. 以旧 Go V3 bytes 为前缀明确换成版本4，再追加24B schema/features/epoch/page/reserved 的静态 golden；3. 截断、坏策略、未知feature、错epoch和旧V3 parser拒绝V4；4. V4 canonical reply extension 绑定 exporter context、三cipher的76B HKDF c2s/s2c domain separation；5. 原 Go V3 三cipher政策可编译/解码。

**明确不声称**：探针的 V4 拓展包装是 R0 夹具，**不是**已经接入原 Go 正式 TLS protected admission 的实现；旧 Go 实现本身只支持 V2/V3 且应该拒绝 V4。真实TLS握手+V4服务端epoch分配/账号验证/rotation/replay/KDF双方一致、Go↔Rust C ABI、目标平台驱动/Windows与ARM、产品及性能均待后续独立 Actions 门。任何绿色不将这些 NOT_RUN 写为 PASS。

**done_when**：新的 S 提交代码/验证契约；观察 Actions 精确build/consume jobs 与 artifact/失败日志；留下对应证据、独立 cursor-only H。此子任务结束不等于整体R0 done_when，M1–M4仍reserved。

**下一动作唯一**：把本次通过的 V4 前缀/epoch/KDF 契约接入生产受 TLS 保护的 Go admission（旧 Go 安全拒绝边界保持），以真实 TLS request/reply 和错误路径跑跨 peer 对照；再进入 Go↔C ABI 探针。
