# PLAN029 H1763｜H1762 32KiB Direct TCP回程仅12KiB：内核关闭期保留精确NAT

- [H1762签名Action43457097827](https://github.com/lly8666/wbd-next/actions/runs/43457097827) [原始压缩证据14054509049](https://github.com/lly8666/wbd-next/actions/runs/43457097827/artifacts/14054509049)：真实Windows Go/Rust TLS/Wintun+MTU1329/Ready、CN DNS/FakeIP Direct UDP与Tunnel UDP、精确Defender、测试专用WSL2 HyperV TCP46112 Allow/读回/失败清理均PASS。Linux物理TCP收到32,768B+FIN，发送32,768B；Windows应用通过FakeIP收到12,288B后`recv` 20s超时。**真实Direct TCP仍FAIL**；未进入非CN Tunnel TCP及最终Stop验收。
- 首个剩余实现风险在`NativeTcpActor::tick`：用户态双腿EOF且用户态缓冲为空就直接`nat.retire`与`retire_flow`，但Windows内核仍可能等待原始客户端ACK或重传尚未送完的TCP/FIN。这会使后续synthetic→FakeIP源/端口反写丢失。属于可证伪假设，未捏造实际内核丢弃点。
- H1763保持单后端、原Go/Rust收发、原WinSock TCP、无额外WFP：接受的Direct TCP用户态两腿结束后仅保留精确NAT+FakeIP引用**60秒纯元数据退役宽限**；从原coarse tick限额64的到期队列回收，无payload缓存、无额外线程、无每flow timer，已关闭映射不让10ms owner loop空转。旧硬16384上限仍生效，满只拒绝新Direct，压力解除后槽回收；未建立连接立即退役。Rust定向单元验证关闭后仍可反写、到期回收和硬满恢复。
- 本批冻结SOURCE后仅一次Normal签名D1/D2 TCP复测，后继029出站Tunnel TCP与owned Stop同Action；若仍失败首错转Wintun回注/邮箱而不是重复Defender探针。DNS的D1–D5、GUI实际配置、padding、P1–P2和性能仍OPEN，028限定收口/030不动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Signed H1762 Linux received+echoed 32K, Windows FakeIP returned 12K FAIL; H1763 metadata-only reverse NAT grace pending native"}
```
