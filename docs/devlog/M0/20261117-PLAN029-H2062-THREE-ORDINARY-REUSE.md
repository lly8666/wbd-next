# PLAN029 H2062｜三条日常真实场景共用 H2061 预编译原生产品（施工/测试入口）

- 分流方案不再改代码，取消本批极端资源、慢盘、崩溃、长 CPU/RSS 测试作为收口前置；它们原始 NOT_RUN/FAIL 保留，不改 PASS。
- 复用产品 SOURCE `0e57cab2d53e2c95962eb673050fa54695fd3665`，Action [44007996775](https://github.com/lly8666/wbd-next/actions/runs/44007996775)：Windows 编译二进制和 Linux peer artifact 已上传；该旧 run 仍卡 WSL2 boot，原生业务资格 **NOT_RUN**。新 fixture 是本批提交 SHA，在每个新 Action 的报告分列 product_binary_source/fixture_source，并逐文件校验 manifest SHA256；产品路径 `crates/`、`r0/go_overlay/`、manifest 没有改动，不能混成一个新版本。
- 一次推送通过 wiring-contract 作一次幂等 fan-out，`gui_reconnect`、`domain_reconnect`、`dns_ttl_restart` 各自独立 workflow_dispatch/Windows VM/原生 Ubuntu WSL2 guest；协调 push 无第四次 native scene；如第一次 GH 事件已存在不重复派发。所有业务使用原 TLS、Npcap/Wintun、物理 DNS socket；没有代理框架、特权 WFP guard、新 watchdog 或全局防火墙调整。
- Domain 见原 `m0_plan029_bootstrap_tc_real_guest.py` 扩展双世代 TC，同一物理 resolver TCP/UDP53、每个会话独立真实选 IP；SNI 保持原借站域名。TTL 见 `m0_plan029_h2063_ttl_real_guest.py`，只把三个独立 txid 和 TTL=2s 记物理真实查询数；GUI 首代→过期→重连的实际 UDP DNS 答复与后续真实 Direct/Tunnel TCP/UDP 必须全部观察，再清理 owned 资源。
- **当前结论**：所有三个新场景均 `NOT_RUN`，尚不能交付；既有 H2055/H2056/H2059/H2031/H2041 历史签名证明保留，失败和超时原样记录。取得三个 Actions 原始 ZIP、report、hash、Stop 后才更新 evidence/功能卡和 cursor，若任一遇 WSL2 环境阻塞，不虚报产品 FAIL 或 PASS。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback","dns-split-ipv6","client-domain-bootstrap"],"reason":"H2062 three independent source-locked original native tests prepared; all new receipts NOT_RUN before Actions"}
```
