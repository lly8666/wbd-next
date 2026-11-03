# PLAN028 H1040 — 两组 Game4 真实同端口/同 TUN 回归

复用已通过 H1037 的**真实 Linux 3 netns 原 Go 产品二账号 Game2 双组**脚本，不造新网络模拟：新增 `WBD_PLAN028_GAME_MULTI_MODE=game2|game4`，实际编译的相同客户端/服务端二进制分别接入 2×2 或 2×4 条原 Go TLS Game lane，共享一个 443 接收器与一个 Rust TUN reader。

两组认证凭据和安装 identity 不同；各自自动 /32 生效；先 A，随后 A+B 同时真实 UDP echo；只停止 A，再要求 B 独立继续收发；最后检查两组 M4 和唯一共享 reader Stop。实际 Game4 使用既有 4-lane normal Game 模式，不提前冒称 Game4 固定 FEC 双组的质量门槛已全部验。

真实交接和 per-group Health90 90s expiry 是不同义务；H1039 最后组 TLS-BPF 恢复由独立 classic-BPF VM Go 单测验证。H1040 原生 Action 成功前只算源码测试候选。

## 真实双 Game4 同源码结果

[Linux original Go/Rust Action 41642592457](https://github.com/lly8666/wbd-next/actions/runs/41642592457) **SUCCESS**，SOURCE `0a0bd7509f82d754917a2b7a6745276aa2cc6e7f`。二个不同账户 Game2 与 Game4 分别完成 2×2/2×4 原 TLS lane、真实共享 reader /32、双人同时真实 UDP、只停 A 后 B 继续 UDP、M4 精确 Stop。Game4 固定 FEC 双组、90秒自动 dead 仍未单独通过。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1040 native OS source test param: two independently authenticated Game2 AND Game4 groups on same one-port single Rust TUN with genuine UDP and exact group Stop, no protocol or hot-path change."}
```
