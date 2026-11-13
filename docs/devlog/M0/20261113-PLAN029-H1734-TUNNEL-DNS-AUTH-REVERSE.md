# PLAN029 H1734｜真实首FAIL和Tunnel DNS强制唯一endpoint双向还原

- H1733 SOURCE `97f81b60c5c2a1d5a3858520360b267d1df68c87` [Rust Action43401408614](https://github.com/lly8666/wbd-next/actions/runs/43401408614)：Linux scoped PASS，Windows 52 PASS / 1 FAIL，首错旧测试仍认CN DNS53必须`LocalDrop`，而真正新Direct DNS已接管并在缺FakeIP journal时本地SERVFAIL回注，正确行为为`DirectHandled`。保留FAIL日志和证据。同期原Go [43401408400](https://github.com/lly8666/wbd-next/actions/runs/43401408400) Windows源码编译、[跨 ABI43401408444](https://github.com/lly8666/wbd-next/actions/runs/43401408444) PASS_SCOPED，仍非真实产品联网。
- 与修复一起，原Rust TX 的非CN DNS UDP53根据QNAME识别为Tunnel后在原Wintun已复制L3上**仅重写目的地为唯一`dns.tunnel`**再进入原M3/FEC seal；同一原认证Rust RX按client port＋DNS ID和原代TTL把真实resolver源地址改回应用原请求DNS地址，校验IP/UDP header checksum，无其他DNS或物理回退。最多256个共享查询，5秒失效，1秒小表清理，仅UDP53会锁一次Map；其他Tunnel DATA与普通TCP不新套栈。
- 目前只在 private V3 probe；只读Go CLI/GUI V2未正式启用。DNS TCP53完整query与UDP TC同端点TCP仍待写；直接TCP kernel/Defender、无旧WFP产品四阶段Stop+恢复、D1–D5/P1–P2、padding都NOT_RUN。当前SOURCE Win/Linux CI待收。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add original Rust single-owner Tunnel DNS unique endpoint query rewrite and authenticated answer inverse; fix first stale H1733 native Windows DNS test failure; product remains NOT_RUN"}
```
