# PLAN029 H1850｜中断补收 H1848/H1849；P2 首等待边界仅做一次分腿观测

- 收到已完成 [H1848 Action43600601863](https://github.com/lly8666/wbd-next/actions/runs/43600601863)，SOURCE `27de9281`：正式非GitHub Actions试验入口 CN `--split-enable`，签名 Windows Wintun OS Applied、真实Direct DNS/TCP/UDP与Tunnel业务、双端owned Stop，均有报告；结论仅 **PASS_SCOPED**，不是GUI按钮或完整D1–D5。
- 收到 [H1849 Action43600840107](https://github.com/lly8666/wbd-next/actions/runs/43600840107)，SOURCE `2771bec0`：同VM 1MiB 物理282ms、Wintun Direct37704ms（比值133.702）；Direct connect735ms、上传18515ms、首回包等待1407ms、下载17047ms。应用双腿 `TCP_NODELAY=0` 且同样16KiB/4ms pacing。完整回声相同SHA，2558条持续Tunnel UDP、最长回包间隔47ms、双端Stop均PASS。**P2功能PASS_SCOPED；性能FAIL/OPEN。** GitHub Action绿色只覆盖其定义的功能断言，绝不能当作029吞吐合格。
- H1844 FIFO单独变更曾上传18703ms且38s未完成；当前同时含H1843回程非丢与H1846 RX32唤醒仍耗37.7s。不能凭此指控单个机制为根因，也不能把Tunnel UDP p99报告的0.0ms作为真实零延迟。没有新证据不重复刷原同类P2。
- 先复用现有 Rust `WBD_PLAN029_P2_RELAY_DIAG=1` 的**每秒累积四腿内读/外读/内写/外写及缓冲**，仅在新的 `[plan029-p2-leg-boundary]` 同SOURCE签名P2场景打开，常规产品仍off；只改既有workflow环境，不增加热路日志、内核TCP后端、第二worker或WFP。配套 `[plan029-v3-real-p2-rebuild]` 新SOURCE单场测试，观测是否为内外socket读取停滞；具体ACK/窗口/重传需有额外证据才归因。**本提交时新诊断测试NOT_RUN**，不与H1849重复dispatch。
- 未完成仍包含Game4 CN、GUI真Connect/Stop、IPv6/中断恢复、D1–D5剩余、P1 CPU、慢FakeIP持久化/压缩与资源压力。PLAN029保持IN_PROGRESS；PLAN028限定收口和PLAN030未开工不变。

```feature-impact
{"kind":"none","ids":[],"reason":"Recover source-locked H1848/H1849 native outcomes and gate pre-existing 1Hz Rust leg diagnosis only for one newly tagged real P2 Action; no product behavior change."}
```
