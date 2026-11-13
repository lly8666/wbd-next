# PLAN029 H1709｜首个TCP EOF丢失修复、DNS查询级模块并行开发

[H1708 Action43359821251](https://github.com/lly8666/wbd-next/actions/runs/43359821251) SRC 171f7371d75a0416a53a48d13b83f7c47d02d9e6 **FAIL**。真实Windows应用经签名Wintun→Rust NAT→Windows内核SYNACK逆改/Accept→物理绑定Rust TCP→独立Ubuntu Linux guest，逆向Windows应用确实收到全部TCP回复字节。但Rust先声明两腿EOF完成即结束Wintun reader，最终内核FIN尚未实际通过逆NAT到应用，Go ReadAll仍超时15s。真实guest与HyperV精确owned清理通过，不把DATA正例冒充成功Stop。

本批只把H1706诊断Rust循环改变为两腿EOF完成后**继续读取唯一Wintun ring**，直到见原Windows客户端FIN和内核listener FIN并经Rust逆转换回注，才返回PASS；否则返回含app/reverse/FIN阶段的首错。对普通Tunnel TCP/密文/FEC/标准TLS无变更。

并行增 `v4_client_dns_answer.rs`：稀疏DNS reply ID/QNAME/class、压缩指针、CNAME链约束多A/TTL，拒绝无关additional反向CDN污染，NXDOMAIN/AAAA/HTTPS/SVCB不生成A。增 `v4_client_dns_pending.rs`：256级事务同QNAME+qtype+resolver+lane+policy_revision合并、保存每请求ID/源tuple、严格回复源与方向、TC=1仅同endpoint TCP后续、超时/Stop局部取消、超限不换DNS方向。**仅纯逻辑源码**，尚未实际DNS UDP/TCP socket、FakeIP分配/持久化、GUI/Normal/Game4，D1/D3未跑。本SOURCE需先接受Linux/Windows单测和原H1706真实网络场景的自动一次测试，首错定向修复。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport"],"reason":"Preserve H1708 real native TCP payload PASS but app EOF FAIL; add sole Rust Wintun FIN drain and bounded DNS query reply/CNAME/concurrency source without promoting product readiness."}
```
