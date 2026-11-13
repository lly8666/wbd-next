# PLAN029 H1729 | 两平台结果与 V3 独立 ABI 检验

- H1728 `ee150cea` 的 [GNU cross ABI 43395844204](https://github.com/lly8666/wbd-next/actions/runs/43395844204) 与 [Windows/Linux Rust 43395844439](https://github.com/lly8666/wbd-next/actions/runs/43395844439) SUCCESS_SCOPED。另一并行写者已修复大小写 WinSock 导入名；本批保留，不重复更动。
- 新增实际原Go `V4WindowsColdSplitConfig` 到私有 Rust V3 104字节/偏移/数量及错误输入负测；同源 Windows Rust build 显式启用 `m0_v4_probe` 以验证真实导出 DLL。测试结果尚待 CI。普通产品 V2 不启动此私有 V3。
- 这些检查仅证明链接和冷策略 ABI；正式 kernel TCP+DNS/Defender owned Stop、系统 DNS/GUI 联网有效、D1–D5/P1–P2/padding 尚未执行，仍 NOT_RUN。

```feature-impact
{"kind":"none","ids":[],"reason":"Only independent original-Go/Rust private V3 ABI tests and source-locked CI compilation; no new product behavior or promotion"}
```
