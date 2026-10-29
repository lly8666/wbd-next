# PLAN027 H400｜外层纯 ACK/SACK 严格报文边界（生产接线前置）
2026-10-30。恢复 main 926845e500fe33ed34f9d39c70acae890492cdbc、M0 cursor H399，回收 [H399 governance40945751731](https://github.com/lly8666/wbd-next/actions/runs/40945751731) SUCCESS。未重派 H396 同源 native。
- `wbd-platform::ipv4_tcp` 新增严格 ACK-only SACK builder：0..4 个范围，标准 NOP/NOP/SACK options，原无 SACK 的 40B ACK 字节保持不变；真实 MTU、校验和、无 heap/AEAD PN。
- `rx_ipv4_tcp` 新增独立 strict pure ACK parser：仅可信 tuple/persona/DF/校验和，SACK 需原握手能力显式开启；仅返回 **unauthenticated presentation hints**，绝不刷新 Health、认定业务交付或改变 PN。DATA 仍走原 M3 AEAD 入口。
- 两个 required 平台反例测试：0/4/5块、MTU、无 SACK golden；带 SACK 的纯 ACK checksum、能力拒绝、与 DATA 隔离。main push Actions 将验证精确源码。
- **本批尚未接入 Windows/Linux RX/TX owner**，没有线上 Receipt 退役、ACK 缺口重传、Quality/Auto、PLAN027 A/B/C PASS。后续先接双方真实生产 owner，再测试，勿以本纯解析器声称完成。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Add source-only bounded strict pure ACK/SACK parser/builder prerequisites with negotiated capability guard; production shadow retirement and network qualification remain NOT_RUN."}
```
