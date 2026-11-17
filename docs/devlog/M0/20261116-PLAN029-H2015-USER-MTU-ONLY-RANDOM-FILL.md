# PLAN029 H2015｜用户覆盖之前所有填充预算与共享CDN专项

- **同一海外 CDN IP 的 CN/非CN 两域名反向出口不再开发/不计029门槛**。H2010–H2014已有失败与未跑结果保留，不再派发或宣称通过；普通CN/IP分流、单DNS和不同IP代表仍验。
- 每条合格 Normal Tunnel TCP/UDP加密record独立随机0..min(500,实际M1外层record_wire_mtu余量)B。去除256-flow映射、12record限制、流累计2KiB、10%比例和1–2s窗口。不等待业务、不向Direct填充、不重新seal老密文/改变协议。
- 修正原 `v4_owner_crypto.rs` 两处 `>256`、`v4_windows_owner.rs` 一处 `>256` 为 `>500`，否则策略生成256B以上填充会在原PN/SEQ拥有者处失败；原M1单测改验400B同样连续PN/Seq。
- 本SOURCE Rust单测和Windows/WSL2原生真实物理加密抓包/Stop仍待Actions，旧H1799仅历史预算下真实NPF copied 16条/50B。
```feature-impact
{"kind":"updated","ids":["startup-flow-padding","dns-split-ipv6"],"reason":"User removes shared-CDN double-domain contrary-egress from scope and sets per-Tunnel-record 0..500B with only actual record MTU bound; eliminate per-flow budget and synchronously raise two crypto plus one Windows owner cap."}
```
