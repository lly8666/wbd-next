# PLAN029B H2093｜B2新真实首错是DNS问题不匹配，先只取有界原始包头

H2092 [签名Action44065841651](https://github.com/lly8666/wbd-next/actions/runs/44065841651) 源 `a73d170fcd2a029a224da385e23f5b149c5cf6b5`：cheap、原Windows Go/Rust与Linux Rust、同源码Linux Go+Rust二进制构建、Win签名Npcap/Wintun安装及WSL2原TUN启动均PASS。原ZIP artifact14320149028 的 **真实native业务FAIL**：Linux `m0_plan029b_b2_cn_guest.py:57` 收到的某个DNS物理/TUN UDP与期望CN/非CN A question不相等，抛 `B2 wrong real upstream domain/question`；随后Windows原Winsock CN应用收到不合格的原DNS ID/状态/问题并失败。H2091原ZIP里Windows应用四阶段确实独立PASS，但并不证明H2092本轮通过。本次**不能再推定只是一次允许的重试，也不可放松DNS出口/QNAME校验或升级为B2 PASS**。

目前日志没有记录坏报文的原始flags/问题，无法判明是应用重复时带了EDNS/不同flag、OS独立系统查询、错向投递还是产品内部DNS ticket错误。H2093仅对Linux测试端首次不匹配打印**有界**socket出口标签、实际Windows/lease IP+port、DNS 12B头、最多48B question hex、预期目标问题与当前已确认事件；同时对合法上游打印每方向实际尝试计数/txid，对Windows原应用首次错误只打真实DNS响应12B头和最多48B question。全部只在外部夹具、小样本、异常/最多4个有效DNS报文，不修改Rust/Go生产代码、实际业务或WAL/owner；任何错误QNAME/qtype/来源或第三次上游仍直接FAIL，绝不无声丢弃后标绿。

下一步根据**真有界首错**决定是否实际源产品有路由bug/Windows额外DNS/报文格式问题，修首个根因而不是扩大测试范围。原H2091/H2092真实FAIL保留。H2089 B0 [Action44056378053](https://github.com/lly8666/wbd-next/actions/runs/44056378053) 的独立signed PASS_SCOPED保留，B2/B3/B4/B5尚未完整收口；不自开PLAN028/030。

```feature-impact
{"kind":"none","ids":[],"reason":"H2093 adds bounded first-invalid DNS header/question and lane diagnostics only to original external Windows/Linux B2 test fixtures; product network code unchanged"}
```
