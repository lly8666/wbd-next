# PLAN029 H1810｜收三份不同 SOURCE 的确定结果

- **H1808** SOURCE `c39a59ab79deebae52422f4a3463960a4f531a98` [Action43565563279](https://github.com/lly8666/wbd-next/actions/runs/43565563279) job132359785457：原始 signed Windows2025 Wintun/Npcap→Linux WSL2/TUN Normal，25s业务 rc0，CN CNAME+两条真实A写出两条互异198.18 FakeIP，实物 Direct UDP 回程、32KiB双腿Direct TCP半关闭、非CN Tunnel TCP/UDP/DNS、真实一向DNS黑洞不回退、OS owned Stop 和既有紧急 finally全部硬断言 PASS。真实 D3 多 A但不覆盖压力满、其他DNS边界与P1/P2。H1807 首次旧H1785静态断言 FAIL 保留。
- **H1809** SOURCE `00e1746e2c14942d4c260e2be659bc0655d7246e` [Action43566091583](https://github.com/lly8666/wbd-next/actions/runs/43566091583) job132360155159：真实签名 Wintun Win32 lease与MTU均先 OS 写/读回，第三DNS intentional fault在真正OS写入前发生，持久 v2 WAL 精确 owned/owned/intent，再同代反序Recover/已断开OS和 WAL sidecar absent。没有再造 watchdog/guard、不模拟掉电、不触碰foreign。D4仅部分 Apply 代表正例。
- **H1807** SOURCE `53b838a2d37d91ed5696e30c0ead9311e0615db5` [Action43565277853](https://github.com/lly8666/wbd-next/actions/runs/43565277853) native Linux aarch64：复用编译单一Rust测试程序，PLAN029 50/50、Game4 调度13/13、FEC调度12/12；不是ARM真实TUN出网、不是Windows Game4分流接线。Windows/Linux x86 H1805纯单测和旧模式历史实测不重跑。
- 以上分别写原始SOURCE和明确 NOT_RUN，卡片不泛化；cursor最后真正有实网业务的 SOURCE 是 H1808 c39，仅在 evidence_refs 使用同源 D3，H1809 和ARM放 context_refs。029仍 IN_PROGRESS：D5 GUI effective/万级规模、P1/P2 CPU/GiB p99 gap queue age、IPv6与Game4 split业务尚待。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-network-wal"],"reason":"Recover three actual independent source-locked H1807/1808/1809 proofs with strictly scoped physical vs ARM pure functional verification, not global PLAN029 PASS."}
```
