# PLAN027 H419｜Linux Go 原 TLS 冷启动 Auto 选择与 Rust 读回

Linux Client/Server 已知 FecV2Auto 配置只在 native worker Start **之前**调用原 Go→Rust C cold control。原 Rust 对当前 Go credential-verified epoch、feature7、无活动 worker/feedback 做双重校验后置位 Auto，Go 随即读回 1；Fixed/off 不调用，不伪造数据认证或额外 actor。只有确实配置 Auto 的 feature7 Native RX 构造四窗口。No per-record Go FFI / packet pump。低频 TX 发送窗、发送摘要匹配和旧 M2 退出仍未完，不报真实业务通过。本批 Actions 待验。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Select Linux original low-rate Auto only from verified Go TLS cold FEC Auto mode, Rust scope-check and exact applied-state readback; existing native worker retains single ownership."}
```
