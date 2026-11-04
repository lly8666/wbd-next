# PLAN028 H1106 — 原生 ARM64 Normal Fixed1 切网资格与 SOURCE 证据字段修复

[Action 41790764503](https://github.com/lly8666/wbd-next/actions/runs/41790764503) SUCCESS；独立解包工件13303750480，与H1104产品SOURCE `32cd752` 的ARM64 ELF/Go/Rust SHA256 manifest完全一致，没有第二次产品编译。ARM64双端原GoTLS/Rust真实网络出口源IPv4 `10.25.0.2→10.25.0.3`，旧64＋新5个真实UDP，外层配置1460、新物理1280、内层OS MTU1195，合法自动IP `10.66.0.150`，Fixed FEC profile1实际applied且pending=false，Rust单reader路由69、Stop/Join成功。源码/日志hash在 `docs/evidence/M0/PLAN028-H1106-SOURCE32CD-ARM64-NORMAL-FIXED-20261104.json`。

H1105 x86 Game4 overlap既有真实 Action41790304416 SUCCESS不变，但当时生成的证据缺仓库治理读取的 `source_sha` 字段（只含 `product_source_sha=0e47d9`），导致 [治理 Action 41790764647](https://github.com/lly8666/wbd-next/actions/runs/41790764647) FAIL。只给H1105证据补相同原产品SOURCE的显式 `source_sha`，将cursor当前最后验证SOURCE指向H1106真实 ARM64 `32cd752`，不更改任何产品、测试结果、旧失败边界。

至此两平台Normal Fixed+Auto短真实切网均有各自原生限定PASS，且Game4 x86 8CH重叠PASS。缺口仍有 Windows实际物理NIC/IP切换、通知到建链与认证到首包耗时和CPU/p99，以及全七模式各自同等范围资格；H998历史热缩MTU失败继续保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1106 native ARM64/ARM64 Normal Fixed1 64+5 real UDP/MTU1195/Stop source-locked PASS; correct H1105 evidence source_sha contract without rerunning product."}
```
