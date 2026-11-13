# PLAN029 H1694｜签名 Wintun 真实内核 A/B/C（新契约 §3B）

- 复核当前 [H1690 原始失败](https://github.com/lly8666/wbd-next/actions/runs/43243971440)：Windows2025 的 native TCP listener 和 UDP self-probe PASS；无新 WFP 时从签名 Wintun 注入 UDP 无到达、TCP 无 SYNACK。默认 Defender BlockInbound 只是线索，**不能证明 drop 组件或选 TCP 后端**。
- 新增一项**不同**的实机诊断在同一 `OpenTUN`、同一 Wintun LUID/owned lease+remote /32/kernel ring/本机 TCP 和 UDP listener 上依次 **A 原状（UDP/TCP SYNACK）→ B 本实例 exact program+protocol+local/remote IP+local/remote port 的两条 owned Defender Allow（有返回/规则读回）→ C 两条由同次随机ID创建的规则准确删除+readback，再新源端口验证 UDP/TCP**。B 若有 TCP SYNACK 继续实检真实 Accept/Data/Reverse/FIN；A/B/C 结果和清理失败各独立记录在 SOURCE JSON，不以接收一个 SYNACK 充当双出口。C cleanup 注册于测试回滚，即便 B 失败亦不能不恢复；不修改第三方规则/WFP guard/全局防火墙状态。A/B/C 失败只保留失败，Allow 没效果仍不排除显式 Block 等其他原因。
- 修改**唯一已有** `m0-plan029-h1669-native-direct-tcp-feasibility.yml` 的诊断内容；由 push-path 一次自动触发，不手动重复 workflow，也不启动旧028矩阵。真实结果须收 Action 日志/产物后另记。A/B/C 程序只有 Netsh 预期允许的一次性 Defender 变更，绝不以 CI 绿色证明 Rust Direct 后端或 DNS 本体。
- 在途收回结果：[SOURCE 9b64 M0-WIN-LINUX #43248553062](https://github.com/lly8666/wbd-next/actions/runs/43248553062) **FAIL** 首个可见产品障碍为 Windows client Ready 前退出，原 Go 错误 `crash-persistent native DNS and IPv6 guard required`，新方案已明确不再要求此旧 guard；不能把旧产品启动失败解释为分流/DNS已测失败。H1692 no-WFP纯测成功及历史 H1686/H1690 失败并存。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Single real signed Windows UDP+TCP ingress diagnostic extended with bounded original/scoped-owned Defender Allow/exact restore A-B-C per PLAN029 §3B; no old WFP or product PASS."}
```
