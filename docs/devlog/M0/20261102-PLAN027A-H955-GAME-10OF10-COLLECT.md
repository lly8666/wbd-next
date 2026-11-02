# PLAN027A H955｜真实 Game MTU新source十场景收齐，复用程序无重编

2026-11-02 主线当前原生代码构建SOURCE `54160ac88b9b41d10f4c3f885879dd68646466a0`，唯一必要新编译 [H952 run 41456643128](https://github.com/lly8666/wbd-next/actions/runs/41456643128) PASS（签名Windows/WSL2 Linux七模式 **legacy1400限定**）；[Windows WAL 41456643143](https://github.com/lly8666/wbd-next/actions/runs/41456643143) PASS。H954调度 [41457592694](https://github.com/lly8666/wbd-next/actions/runs/41457592694) 已按旧产品来源、SHA256及新SOURCE原样引用产物，10个Action均跳过Windows/Go/Rust/Linux重编。

八个Game off/FEC真实双系统新SOURCE+OS MTU数值/Stop **8/8 PASS**：
- outer默认1460：Game2 [41458474044](https://github.com/lly8666/wbd-next/actions/runs/41458474044)、Game4 [41458487303](https://github.com/lly8666/wbd-next/actions/runs/41458487303)、Game2+FEC [41458501914](https://github.com/lly8666/wbd-next/actions/runs/41458501914)、Game4+FEC [41458516672](https://github.com/lly8666/wbd-next/actions/runs/41458516672)。
- outer显式1500：Game2 [41458534163](https://github.com/lly8666/wbd-next/actions/runs/41458534163)、Game4 [41458544890](https://github.com/lly8666/wbd-next/actions/runs/41458544890)、Game2+FEC [41458560346](https://github.com/lly8666/wbd-next/actions/runs/41458560346)、Game4+FEC [41458575604](https://github.com/lly8666/wbd-next/actions/runs/41458575604)。

3Mbps双系统Game4+FEC两场景 **2/2 PASS**：[25ms0% 41458588765](https://github.com/lly8666/wbd-next/actions/runs/41458588765)双向p99约188/182.6ms、[250ms30% 41458603763](https://github.com/lly8666/wbd-next/actions/runs/41458603763)约672/646.5ms。两次真实Windows内层OS MTU读回均1389（外层默认1460），Linux实际内层1298；延迟为夹具业务测量，不是跨OS校准单程时钟。3Mbps资源采样已有原始证据，但不以两台不同runner作CPU因果对照。

H950/H951旧H948已编译程序也真实通过非Game Normal/Fixed/Auto默认1460、显式1500以及Normal3Mbps、Auto5→30→5；这些结果**只属于旧H948源码**，不把“非Game代码没改”伪装成新H952字节同一验收。旧Game遗漏数值回执、两条非法all+reuse前检、H953空结论调度错误全保留FAIL。

**尚未达到完整PLAN027A退出**：真实DF0/DF1与ICMP oversized、Game4FEC原生独立5→30→5阶段、当前SOURCE ARM64、整机CPU/RSS对照资格；PLAN028/029/030还没实装，不能报交付。继续顺序为先这些027A所需差异，再028会话多client，029/030依赖接口。外层普通默认1460B(IPv4 IP不含L2)，1500B只可显式最大。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Record exact 10/10 source-verified new Windows/Linux Game native PASS with pre-READY inner OS MTU numeric readback, while preserving old failures and scoped pending exits."}
```
