# PLAN029 H1750｜首次真签名 CN Direct 双端通过，修 TCP 测试源地址

- H1749 SOURCE `6c82ea087a9081900e0f8ca81d51086dd3eb4a3f` [Action43427819727](https://github.com/lly8666/wbd-next/actions/runs/43427819727) **整体FAIL**，实际 [artifact14039805110](https://github.com/lly8666/wbd-next/actions/runs/43427819727) 同时证实原Go TLS、签名Wintun、Rust V3、Linux TUN和内核双向Tunnel UDP已起效，Windows真实app向8.8.8.8发`www.cn.example`，唯一物理dns.direct Linux socket收到请求并CNAME+A，Rust FakeJournal写前持久后合成FakeIP198.18.0.1，Win app FakeIP:46111收到Linux物理UDP回显。Linux DNS53与业务UDP46111两物理socket均证实Windows外网源172.27.80.1，**首个真实CN域名Direct UDP+Tunnel UDP同代证据PASS_SCOPED**，没有Tunnel回退。
- 整体依旧FAIL：Linux alias203.0.113.77→Win 10.66.0.2:45902旧TCP比较器Win accept 0、Linux echo false；反方向Win→Linux echo true。原TCP脚本listener绑定副地址.77，主动dial却使用不绑定源的`socket.create_connection(remote)`；Linux可能选主TUN 10.66.0.1，与Win test-only Defender入站仅允许remote .77不符。此前没有抓到实际SYN源，故此为**待实网核实的根因假设**，不伪称已证明。
- 仅对原真实两OS Python TCP对照增加`source_address=(local,0)`并立即核验`getsockname()==local`，不更动正式产品Wintun/Rust/Go/Defender规则及所有严格TCP/Stop判定，cheap unittest锁定源绑定。H1750同一标记`[plan029-v3-real-direct-udp]`触发仅一场新签名VM；CI结果待测。
- 正式TCP kernel actor postApply/Defender owned、双DNS完整场景、D1-D5/P1-P2、GUI full及startup padding仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record real signed original Rust V3 CN physical DNS/CNAME durable FakeIP and Direct UDP success with independent Linux source proof; fix test-only client TCP bind source without broadening Defender and retain strict terminal gates"}
```
