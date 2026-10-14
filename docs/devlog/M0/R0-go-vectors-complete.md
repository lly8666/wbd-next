# R0 Go原版V3 + 24B V4 admission golden完成范围

本轮按M0 seq5唯一下一动作施工，未启动worker、未修改旧仓库、未部署。自远端确认role active/main/epoch1，checkpoint `a71f63b` 至开工HEAD `d8ec236` 仅1个cursor-only H，历史run已关闭。

**S与实测**：首次SOURCE `de585696c1ff0b199f2649340a567427295e438a` Actions [38509549705](https://github.com/lly8666/wbd-next/actions/runs/38509549705) attempt1，Go 1.23.12编译旧仓库精确SHA `a7a82db31fe736ffedee330795a3234d358f1984` 的 `internal/realityfront`，加仓内R0纯测试文件。build 115674662759、consume 115674821579；5/5 PASS。根据该run记录原版V3字节、V4 24B字节和Go exporter/HKDF摘要，随后将观测到的摘要冻结为断言，**没有更换配置/seed优化数值**。

最终测试SOURCE `87ad54b044e5faa974d47ba2a7015a75760328cd`，Actions [38509701636](https://github.com/lly8666/wbd-next/actions/runs/38509701636) attempt1 COMPLETED/SUCCESS。build job 115675132618与consume job 115675294926分开：build编译一次，consumer验证SOURCE+legacy SHA+两个输入hash+预编译Go二进制size/hash后直接执行，不二次编译；5顶层测试通过，0失败。build artifact 11869028319 / sha256 `e8af6adcf01bec07ba49fe1ccc1525f38b5dc5226ab585b0f62d6b9273682960`；result artifact 11869257734 / sha256 `bd13f0a7f2d62dec692ba5560058befd35bd02aae69b152d5d471c44a8101071`。这两项是GitHub archive摘要；编译二进制和SOURCE由job内验证，未额外本地下载zip进行独立复核。具体值及限制见 `docs/evidence/M0/R0-go-vectors.json`。

**证据界限**：V3 writer/parser是旧Go实际源码；V4是注入固定旧Go checkout的R0 **测试适配器**，并非生产受TLS保护的admission已接受版本4。原Go仅支持V2/V3，V4在原decoder显式拒绝。测试证明静态布局、负面向量、context hash和3套direction KDF在该编译fixture下可复现；服务端epoch租约、认证/协商/rotation/duplicate、真实TLS Go客户端服务端交互、C ABI、平台ABI/Windows/ARM以及产品性能均未运行。旧遗留N2/N4、80秒下行问题仍OPEN。

**子任务done_when**：已满足已声明的旧Go编译与V3/V4 golden检测；仅本子任务结束。R0总体尚未完成，M1–M4继续reserved。

**唯一next_action**：把V4 24B与epoch/KDF契约接入真正受TLS保护的Go admission入口并在Actions跑真实双方协商及错误路径，随后再检查Go↔C ABI探针。
