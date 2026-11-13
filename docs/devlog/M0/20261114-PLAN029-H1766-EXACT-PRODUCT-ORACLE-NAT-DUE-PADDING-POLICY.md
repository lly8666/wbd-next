# PLAN029 H1766｜实网DNS/TCP/UDP/Stop实测通过，修过期028外层门＋NAT到期唤醒

- 已收 [H1765签名 Action43514792104](https://github.com/lly8666/wbd-next/actions/runs/43514792104)（SOURCE `1ab6d4b5268b9bedc1506598b28fc33f9e485be3`；[原始artifact14080637898](https://github.com/lly8666/wbd-next/actions/runs/43514792104/artifacts/14080637898)）：原始Windows/Go/Rust Wintun/WSL Linux的单Normal真实进程 **exit0 / mode-batch PASS**。本次见证CN域名/CNAME FakeIP物理DNS与Direct UDP，原生Direct TCP真实双腿32,768B回显/FIN，Windows→Linux非CN Tunnel TCP和双向UDP、exact Defender/WAL与双OS owned Stop。另外新增非CN `www.globalx.example` 应用查询发往原呈现 `8.8.8.8:53`，Linux真实TUN唯一 `1.1.1.1:53`收到QNAME并返回 `203.0.113.77`，Windows原DNS源恢复且不是FakeIP。未跑黑洞无回退、应用TCP53、D2海外CDN反例等。
- GitHub外层 **conclusion仍FAIL**：PowerShell的通用 selected-mode gate 不看 029 新业务的outbound方向，强制`tcp_duplex=='PASS_ACTUAL_TWO_OS_KERNEL_TCP'`，而真实当前029测试回执是`PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP`。H1766增加**单独strict**`WBD_PLAN029_V3_DIRECT_SCENE`门：检查当前SOURCE、真实Direct TCP 32768B/FIN/owned Stop、Tunnel TCP/UDP、1.1.1.1非CN DNS原DNS回包；未改变旧028与其他mode条件，不给任意`PASS`字符串放水。保留H1765红灯失败。
- H1763的Direct TCP两腿EOF后的60s纯NAT元数据宽限已经真实解决此前回包12K问题；H1766并行补旧TX一次`wait_ready`调度最早关闭NAT回收时点，不为此10ms忙轮询/多线程，测试提前/到期/无状态时的等待时间以及硬上限流表回收。
- 029填充并行增加**纯Rust有限预算模块**：off/tls/flows策略、256条、12 record、2048B/流、256B/record、≤10%、1–2s、轮换8项到期；这仅是未接线的源/单测，**目前不生成真实AEAD padding、不新增GUI/CLI有效配置，绝不算029填充退出**。后续须沿原LINK seal、MTU/原密文FEC/重传、GUI effective实际接线及OS对照测试完成。
- H1766一个SOURCE自动一Normal signed Action，独立Rust/Go/治理检查可并行；不重复dispatch、不覆盖他人写入、不重开028矩阵、030未开工，D1–D5/P1–P2未完成。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","startup-flow-padding"],"reason":"H1765 signed real dual egress and Tunnel DNS PASS but outer stale TCP proof FAIL; H1766 exact branch, metadata deadline and padding policy source-only"}
```
