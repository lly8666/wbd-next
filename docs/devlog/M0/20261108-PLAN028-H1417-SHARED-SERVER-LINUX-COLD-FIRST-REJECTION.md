# PLAN028 H1417：同服 Linux 客户端真实 SYNACK 后冷认证失败，先补唯一缺的原日志

2026-11-08。收回 [原 H1415 Action42494398656](https://github.com/lly8666/wbd-next/actions/runs/42494398656)，精确被测 SOURCE `0b485b9acad761dc127e93fb35d9c737115b8e7e`，前置 Windows 原签名 Npcap/Wintun 原始 Go TLS/Rust M4 READY、共享服务器原 Go TLS443/Rust READY 已观测；独立 Linux netns/veth 原客户端收到合法 SYNACK MSS1420，后连续有 native candidate `class=other`/重连而未能取得合法 `V4_ORIGINAL_GO_CLIENT_NATIVE_READY`，完整双客户端 L1 **FAIL/NOT_RUN 具体阶段**，不是整体成功。Windows WAL 空、桥/原 IP/默认路由/namespace 精确恢复真实通过。原 CI FAIL 保留。

原因不能只凭最后 `class=other` 推定：原 server 全局 `--peer-persona windows11` 而 Linux client Legacy 假说成立与否，要看真实 `V4_PUBLIC_MULTI_ADMISSION_REJECT` 原阶段；也可能是 TLS credential/record/M4 owner 的另一闭环。原 Action small ZIP 未上传 server/Linux 原始阶段。H1417 不动产品代码、Go/TLS/FEC/协议，也不重跑 x86/ARM64 7档 ISA-L，**只在已有失败路径**输出原 server/Linux/Windows 允许的状态前缀最后24行、每行<=250字到原 stdout 和小 JSON；不含密码、record/密钥、全量日志，完全没有热路径新增日志。等一条 SOURCE Action 的首错阶段再决定最小产品修复。

```feature-impact
{"kind":"none","ids":[],"reason":"Only bounded original product cold-stage evidence extracted by failed test harness, no new wire/probe/hot path/product behavior."}
```
