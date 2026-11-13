# PLAN029 H1748｜真实签名首错与原NativeOwner Direct TCP post-Apply冷准备

- H1745 SOURCE `947c116aec665c196d657ef1aa5974b54c5522e3` [Action43422444895](https://github.com/lly8666/wbd-next/actions/runs/43422444895) **FAIL_REAL**：非CN Tunnel对照TCP的Windows→Linux echo成功，Linux `203.0.113.77`→Windows `10.66.0.2:45902`逆向连接超时，Windows server_received=0；当时test-owned Windows Defender临时规则仅接受旧10.66.0.1。CN Direct DNS/FakeIP/UDP尚没开始，不能据此判断Direct产品失败。H1746修临时规则、H1747 self-trigger重新启动签名Scene；H1747实网步骤第一条实际错误仍在取日志，不编造结论。
- 同时修真正产品Direct TCP架构：Rust私有V3原先在`NativeSplitWorker::new`（Go四阶段OS Apply之前）就想`TcpListener::bind(lease,0)`，lease尚未生效且Windows系统分配的端口未知，绝不能靠预先开放随机/通配端口骗过Defender。
- 本次Rust禁止`ColdSplitSourceV1.tcp_owned!=0`预提前启用，保存cold的198.19/16 synthetic /32、Wintun lease、underlay、ifindex等计划但不建立socket。新`WbdWinNativeTcpControlV1`长度48B的同代 owner/epoch/LUID/index校验接口仅通过原Rust TX一槽冷命令，在**真正OS Apply之后**才可`PREPARE`建立Windows内核listener并回传真实端口；直到Go获得本代synthetic /32 route和针对本租约/此端口的精确Defender Allow及读回前，NativeSplitWorker对Direct TCP和本代synthetic响应仍LocalDrop。若Stop竞态、身份错误或命令timeout则拒绝，不给假Ready。Go bridge目前**只公开PREPARE**且要求ProductApplied，不允许擅自发送ENABLE，产品仍不激活TCP。
- Rust/Go FFI各自增加48B ABI字段偏移及提前cold拒绝测试，现存original V3 128B不扩，live manifest result_blob更新；仅源码、WIN/LINUX Rust及原Go compile待真实SOURCE验证。其余Normal/Fixed/Game4数据面和Old WFP不变。
- 后续完成当前代Defender规则写前WAL/读回/CAS撤销，最后才能从真实Go post-Apply发ENABLE，跑签名Direct TCP与D1–D5/P1–P2、startup padding。PLAN030不开。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add two-phase authenticated original Rust NativeOwner Direct TCP listener preparation after real no-WFP OS Apply with 48B Go/Rust FFI and strict pre-Defender fail-closed mode; preserve genuine H1745 reverse-TCP first failure"}
```
