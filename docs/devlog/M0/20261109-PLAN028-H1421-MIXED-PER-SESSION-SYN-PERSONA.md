# PLAN028 H1421｜同一端口 Windows11 与 Linux Legacy 同服每会话冷 persona

2026-11-09，[H1420 原 Action42500155410](https://github.com/lly8666/wbd-next/actions/runs/42500155410) 源 `66fb7f29a6ec65c199b94fb541fcd2c01b5de581` 原始 ZIP13625548105 CRC PASS，完整原 Windows signed Wintun/TLS/Rust Alice 264/264 UDP echo、259 反向正常；独立 Linux netns Bob 通过 TLS/Rust M4 READY，TUN /32 到服务器内层 OS route-get PASS，收服务端主动 reverse229，但自发236仅3 echo。两条已认证 owner READY，表明不在握手/路由/客户端接收，B 上行回显稳定失败。原 Action FAIL，TCP/Stop存活 NOT_RUN；Windows WAL、bridge netns/IP/原路由恢复 PASS 不改变原结论。

现行 product 根因：共享 server `runSharedMultiServer` 用整个进程 `c.peerPersona=windows11` 启动所有 `V4LinuxServerProduct` Rust RX，Linux 真原客户端发 Legacy TTL64。Rust `rx_ipv4_tcp::parse_data_packet` 对其 credential-Go 下发的 `TrustedRx.persona` 严格核对 TTL，Windows11 预期128，B C2S DATA因 WrongPersona 被拒；Linux B 的反向可达是切实区分定位的证据。不能为通过放宽 Rust TTL/AEAD/PN。

H1421 只在原 Go `faketcp.ParseIPv4TCP` **冷 SYN**中识别已有标准 MSS/SACK/WS 选项次序（Legacy vs Windows11），缓存到原 `ServerAssociation.PeerTCPProfile`。共享 server 启动**每个已经过原 credential TLS 的** Rust owner 时用相应 persona，不重构握手、单端口、M4共享 TUN/FEC/record/驱动，也不增加任何稳态包头或热探针；未知 SYN 仍用显式原 server persona，维持旧业务。两端相同源构建后，在一个 Windows＋独立 Linux 原生场景中强核服务器收到 Windows=1/Legacy=0 的真 M4 readback 和双向 UDP/TCP/owned Stop。失败需原样记录。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct existing original Go per-session cold peer presentation choice for already-protected TLS/M4 owners on mixed Windows/Linux shared server; no public settings, wire, record or FEC changes."}
```
