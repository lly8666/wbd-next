# PLAN027 H426｜回收 H425 SOURCE Actions，修正旧 64 包 Auto 冒认成熟证据

恢复 main 的 H413 checkpoint 后 15 个提交（H414–H425），当前源头 69bbe53c：Windows 双向低频 Quality 生产接线、Linux Auto START/CLOSE、实际 M4 firstsend F、匹配 Quality 回传和 Auto 读回替代旧逐 record bitmap 已落代码；**Fixed/off 旧 M2 和外层 ACK/SACK 退休仍未完成**，不能把部分替代写成 PLAN027 全部完成。

真实 Actions 40976092890（H425）Linux keepalive 单测 PASS，Auto original-Go netns job FAIL：同 SOURCE 固定 FEC2 64 包业务 delivered=64，随后旧验收要求 `mode=auto applied=1 pending=false`；实际 `requested=1 applied=0 pending=true`。新质量发送窗口跨度 1024 PN，64 包没有完整闭合、成熟、回传的有效样本，因此不应从旧 M2 报告或空窗口伪造 applied。H424/H425 之后旧 `M0_PLAN022_*M2*` 正例不再是 Auto 合格 oracle。此 FAIL 保留；该测试不是 PLAN027 A4 升降长测。

本批仅修复真实双端短 smoke 的断言与标记：Fixed 仍要求其历史 M2 APPLIED（等待后续产品替代），Auto 只核真实首到/Stop/模式读回，显式输出 `PENDING_QUALITY_NOT_QUALIFIED`，**不宣称 Auto APPLIED 或 A4 PASS**。对应 workflow 的 marker 同步。未降低生产质量门槛，不调整 Auto 低损判定，不发起新矩阵。Actions 会对新 SOURCE 自动验证；回收后才可把此源 smoke 判定为 PASS。

H425 另有同源 40976093067、40976092884 仍在途，回收前不得重复 dispatch。下一步继续 PLAN027 §0-1：完成 Fixed/off Receipt 退役和真实 ACK/SACK 退休、两端 Health/Auto 质量读回，构造 1024+ 有效窗口与持续 120s Auto A4；再 A2/A3/A5、B、C、结果修复与交付。容量不免除独立待办。

```feature-impact
{"kind":"none","reason":"Only corrected obsolete sparse Auto smoke assertion/marker and its source-locked workflow; no product mode, config, ABI or runtime behavior changed."}
```
