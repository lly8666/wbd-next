# PLAN029 H1914｜复用构件二次10GiB实测CPU已复现，立即重排空转有可重复证据

- [H1913签名原生10GiB Action43704703993](https://github.com/lly8666/wbd-next/actions/runs/43704703993) **COMPLETED SUCCESS**，不同于H1911 YAML/H1912 static red history。本次原VM确实下载H1909 `source_sha=64f6819460f7f950f13bc7d10659a6f4552b28b6` 已签名Win EXE/Rust DLL和WSL2原Go/Rust两个artifact，Git源/ABI差异为空、run成功/manifest+文件SHA256、实际DLL V3导出、签名Npcap/Wintun、所有Stop执行成功。GitHub本次`GITHUB_SHA=4f7a3481e9c48f83869b5d4e98a39a976c1bca61`仅是fixture+workflow变化，**不许把测试源码误报为实际Windows DLL编译SHA**。Windows Go/Windows Rust/Linux Rust/Linux产品四种昂贵编译作业真实SKIPPED，cheap PASS。
- 同机原进程CPU/GiB（original Go+Rust进程含Tunnel小UDP、不含驱动ISR/DPC）单向2GiB每路径：物理0.242188 vs Direct9.304688, 增量**+9.062500**秒/GiB（用户+4.945313、内核+4.117188）；实测Mbps物理500.008、Direct499.997。1.5GiB每方向全双工每路径：物理0.255208 vs Direct7.885417，增量**+7.630209**（用户+4.208334、内核+3.421875）；Mbps物理699.996、Direct700.003。96B Tunnel UDP在Direct单向p99=1.212ms，双向=1.416ms；所有原始TCP SHA/FIN和双owned Stop PASS。
- 原H1909同一产品SHA另一个VM为增量+11.210938/+9.317708 CPU秒/GiB；复现趋势为“CPU远高于物理基线”，H1909/H1913的数字差异**不是代码优化**，因二者产品字节完全相同、不同WindowsVM。H1913原Rust终结计数：WinSock shared wake121,511、socket checks243,008、effective ready peak1、queue oldest2ms、relay回合274,595，**零进展93,796(34.16%)**。H1909相同编译字节另VM 231,572回合，**零进展87,237(37.67%)**。这明确支持减少`NativeTcpActor`在read/write有进展但数据全部直送、无backlog情况下的无条件立即requeue，不能因其余零进展而忙等或提升多线程。
- H1913独立 [governance-maintenance Action43704703990](https://github.com/lly8666/wbd-next/actions/runs/43704703990) FAIL唯一个静态测试字符串：原workflow用`(github.ref_name == 'main' && contains(...)) ||`，H1911新断言却错误要求`contains(...) ||`（少两个闭合括号）。本次修正为**真实完整片段断言**，删除旧无效`if False`测试死码，其余H1909 run SHA、source/ABIBIN、CPU/Stop、历史M4无改动。
- 下步生产修改是最小化原Rust TX ready重排：只在64KiB整段内核可读后可能还有数据、或缓冲区仍有有界待发尾部时自我requeue；否则等待已有真实`FD_READ/FD_WRITE/FD_CLOSE`，不改原16 WSA event shards/单TX owner/固定8flow量子、TCP FIN/backpressure/NAT。先做Windows Rust实编译与组件，签名原生4MiB及长10GiB对比，不把不同VM数当严格A/B。PLAN029 P1/P2性能仍OPEN，PLAN030不启动。

```feature-impact
{"kind":"none","ids":[],"reason":"H1914 collects signed true H1913 same-artifact H1909 10GiB CPU and Rust no-progress evidence, fixes one malformed strict static assertion; no native product/feature code change."}
```
