# M0 main PLAN012 首个真实错误：FEC RX 全绿却被旧固定计数误红（2026-11-22）

旧 [Action 45032248693](https://github.com/lly8666/wbd-next/actions/runs/45032248693) 真实原始 artifact `m0-plan012-combined-45032248693-1` 的 `fixed-kernel-result/continuous-rx.log` **确认为 `test result: ok. 5 passed; 0 failed`**，原工作流却执行 `grep -q 'test result: ok. 4 passed; 0 failed'`，使首个 Build 步骤 fail，之后“mandatory exact 1%”仅因上游 skipped 而 fail。其他现存 `release-record.log` 1/1、`game-lanes.log` 2/2、`fixed-tx-stream.log` 5/5 均真成功；这四个日志是唯一该 Action上传的 first-error material，**没有编造后续 Go 编译或网络 PASS**。新工作流将这条断言精确修正为 5 并留 Python 合同回归，未删任一真实测试、未放松丢包/Stop 条件或产品代码。

本 Action 之前添加的 `tls.go`（旧 original Go 的 `ClientConfig.RootCAs` compatibility）和源锁 `FakeTCP/MSS` 仍在；只有过了源锁 native Rust 门，才能实际证明后面的 Go TLS 和真实1%网络关。若下一 Action 再红，必须追新 SOURCE 的实际第一个失败，不把旧第一层绿当整个 PLAN012 绿。

## 第二关：Rust 单元全通过后仍未进入 original-Go 的 ABI 断言

更新后的真实 [Action 45032506054](https://github.com/lly8666/wbd-next/actions/runs/45032506054) 工件同时证明 10 个独立原 Rust 阶段的准确结果：default/opt-in release BUILD 完成、release record 1/1、game lanes 2/2、continuous RX 5/5、fixed TX 5/5、五条 PLAN028 shared-TUN/route 各1/1，然而 **没有`original-go-game-tls.log`**，故当前红灯出现在这些 Rust 检查完成、original-Go 命令开始之前。对应工作流仍有11个 `nm -D libwbd_engine.so | grep -q` 通过 `set -o pipefail` 并列调用；`nm` 遇 `grep -q` 提前返回可能 SIGPIPE=141，造成**有符号却红灯**，但在旧 run 缺少符号列表时不能断言它一定是原因。

后继修复将每次真实 .so 的 `nm -D` 先存 `default-abi-symbols.log` / `opt-in-abi-symbols.log`，随后用11个逐项`abi_req`对同一只读符号表核对**完整正确名字**，缺任何一个仍真FAIL并打印缺失名字，且将源列表保存在 FAIL artifact 中。没有消掉 Go/真实1%网络关，也不把前级 Rust PASS 冒充全部原Go PASS。待新 SOURCE 真实重验后决定是否需要继续改动。
