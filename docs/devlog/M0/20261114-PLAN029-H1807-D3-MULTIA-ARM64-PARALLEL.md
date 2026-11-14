# PLAN029 H1807｜一批并行补 D3 真多A与 ARM64 模式代表

- 基线 `d7d2c478bb615d2ba322e2d561aa6694d5d3f857` 当前无在途 Action。新 signed Normal 场景由 [plan029-v3-real-d3-multia] 唯一触发，使用原 Windows Go TLS→Rust 单 Wintun/Npcap 与 Linux WSL2/TUN、owned DNS/Defender/Stop。不重跑额外 cache/TCP53/Direct8/padding 特例：Linux 真实 DNS53 回 CNAME+2 个不同 A、Windows 内核应用收到两条不同合成 FakeIP 且不能看到真实 CDN A，再用第一条实际 Direct UDP 到 Linux 物理 socket 回程，源锁和两端 Stop 硬断言。
- 另起独立 Action 在 **ubuntu-24.04-arm** 原生 aarch64 执行，Rust lib 单源码 release --no-run 一次编译，依次运行 PLAN029/DNS/Full quota、Game4 原 Rust 调度、FEC 定向 unit filter。Windows x86/Linux x86 当前已有 H1805 真机纯组件绿色，Linux ARM64 先前交叉编译结果不是原生 ARM 测试；本批不刷已知 x86 单测与 028 全组合。ARM 新场景只称纯本机代码，不称真实 Wintun/ARM 网络。
- 仅夹具/Actions/cursor，不改正式产品 packet/DNS/GUI；仍待 D3 小额度真实恢复、D4 真实 OS/IPv6/断开、D5 GUI、P1/P2 与 Game4 分流真实接线。结果 NOT_RUN，须核准确 SOURCE 和 Action。

```feature-impact
{"kind":"none","ids":[],"reason":"Only add independently scoped signed D3 multi-A witness and ARM64 native pure representative CI; no product runtime/default/config behavior changes."}
```
