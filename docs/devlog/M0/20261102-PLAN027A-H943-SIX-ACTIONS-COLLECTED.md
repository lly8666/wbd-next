# PLAN027A H943｜六场手工 SOURCE 锁定真实原生 Actions 全部收取

手工派发 `41446575641` 成功，唯一产品/脚本 SOURCE `ae3e7e9f52c415b60d596b7e923ade07f463d4ed`，真实签名 Windows NPF/Wintun + 原始Go TLS/Rust owner + Linux WSL2 TUN；六场均 completed/success，非仅队列、编译或假定的 PASS。M0 保留 H931 Fixed rc1、H935 E0502历史失败。

精确结果在 `docs/evidence/M0/PLAN027A-H943-ONE-SHOT-1460-1500-20261102.json`：默认1460 **不传 Windows --mtu / Linux --outer-mtu** 七模式 `41446644468` 7/7 duplex/Stop PASS；显式1500双端 `41446654756` 7/7 PASS。Linux实际内层MTU按 Normal1329、Fixed/Auto1315、Game2/4 1313、Game2/4FEC1298，均独立于用户外层意图且较理论无额外限制上限保守。

1460 10Mbps/25ms loss0 60s：Normal `41446664669` first(win/linux)=1/1，吞吐10/9.9973Mbps、round-trip p99=47/51.627ms、owned Stop PASS；Game4FEC `41446675044` first=1/1，吞吐9.9999/9.9972Mbps、p99=1297/1327.63ms，虽然功能PASS但**性能显著疑点**。弱网250ms30%：Fixed `41446684870` first=.99947/.998818、p99=532/540.915ms，Game4FEC `41446696380` first=.997094/.998832、p99=719/696.615ms；都是真实kernel、Stop PASS，不承诺零丢；比较只看同源，不能把不同独立VM的CPU数字机械当A/B。

四场每个均60秒。全部 p99 指发送端本地钟的往返，不是跨OS未校准one-way；日志 `generator_cpu_s`是业务发生器耗时，不是Rust产品CPU-s/GiB。重点剩余：Windows numeric Wintun OS Applied读回、实际DF0/DF1巨UDP/IP options/ICMP/EMSGSIZE、5→30→5真实波形及 Game原设计3Mbps容量CPU/RSS/p99对照。不允许因6/6绿色 Action宣告整个027A达标或提前进入028。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Record six exact-source Windows↔Linux real native default1460/explicit1500 and scoped 1460 loss0/loss30 functional passes, preserve Game4FEC performance p99 caution and DF/native oversize NOT_RUN without global promotion."}
```
