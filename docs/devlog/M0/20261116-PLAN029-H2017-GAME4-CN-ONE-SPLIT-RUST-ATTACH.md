# PLAN029 H2017｜四TLS Game4 Rust共享分流接线与用户最新范围

- 2026-11-16 用户明确**同一海外CDN IP的CN/nonCN两域名相反出口不要求开发或作为029验收门**，已在计划/分流契约中标记NOT_REQUIRED。原H2010–H2014失败保留，禁用新增专用Action标记。
- 真实 Game4 保留原四个Go TLS/FakeTCP 连接、同一Rust GameAdapter PN/FEC/outer修复和两个Win32 worker/单一Wintun。V4仅对显式`split-enable && bypass-lan-cn`冷接入原Normal`NativeSplitWorker`：Game TX先按QNAME/IP决策，把Direct交物理TCP/UDP socket、Tunnel DNS业务重写后原样提交GameAdapter；Game RX在同一原Wintun writer递送真实Direct回程，已认证Tunnel DNS还原源。上界为16 TCP shard + 16 UDP event + Stop/tun/wake，无额外Go逐包泵/第二Wintun；Game4 Off原V3路径保持原样。
- 四阶段OS Apply/LiveReceipt/数字MTU通过后，复用同一WAL带代际synthetic TCP /32及**精确owned Defender Allow**的PREPARE→readback→ENABLE。任何中间失败仍由同原产品Stop恢复，不能以组件PASS假Ready；Game2显式CN仍冷拒。
- 本SOURCE附带唯一Windows/WSL2签名Game4 off简易实测：原Game4 Tunnel UDP+TCP双向、CN physical DNS→FakeIP Direct UDP、32KiB真实Direct TCP+FIN回程、Linux eth0物理source、单Wintun、双Stop。原Game4 FEC6仍保持未改，暂不要求所有组合。**网络未跑之前状态IMPLEMENTED_NOT_QUALIFIED**。
- H2016取消每流budget/窗口后每条合格Normal Tunnel加密record 0..500B且真MTU裁剪，前版256阈值在M1三处同步更正；原H2016组件绿不替代真实密文抓包/Stop。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","startup-flow-padding"],"reason":"H2017 actual Game4 CN one split worker in original Rust Wintun Game4 TX/RX, cold exact Defender TCP and one real two-OS scenario; source unverified, same-IP CDN exception removed, 500B no flow quotas documented."}
```
