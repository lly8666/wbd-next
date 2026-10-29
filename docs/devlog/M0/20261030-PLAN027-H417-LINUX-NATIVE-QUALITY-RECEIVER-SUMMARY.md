# PLAN027 H417｜Linux M3 认证低频窗口 RX 与原 M4 质量摘要

H416 后继续 Linux 生产接线。原唯一 AEAD/PN/replay 的 BackgroundRxReceipt 暴露认证 START/CLOSE/v2 摘要（不信 TCP ACK/Go 提示）。现有 M4 RX 内核循环用共享有界四窗口处理唯一 DATA/控制，不另开 Go 逐包 FFI/新线程，CLOSE 的本机 3s 成熟后由原 TX AEAD kind1/M4 sendmmsg 发 36B Quality 摘要；实际 copied 才退休，失败保留并继续原 Health。信号处理绑定 feature7 的同一 Go TLS generation/epoch/direction。仅 H417 SOURCE 组件候选，Linux TX START 发送、Auto 策略匹配、全部 M2 退役和 A/B/C 尚待实现/Actions 验证。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Wire authenticated Linux M3 START/CLOSE RX to four-window mature encrypted quality summary in original Rust M4 owner; product not yet qualified."}
```
