# Android CN geosite 第二轮下载源失败与隔离内核 DNS UDP/53 验收（2026-11-17）

历史 SOURCE `4d8301a52202aed1aa3ca4d7b6964c9125e8d0da` [KSU Action43943698950](https://github.com/lly8666/wbd-next/actions/runs/43943698950) **FAIL**：x86_64 / ARM64 Bionic regex 1.12.2 / sha2 0.10.9 编译和 sha 锁验证全部通过，但在 APK 打包阶段固定 `delegated-apnic-20261116` 从 `/stats/apnic/` 被每日轮转删除返回 HTTP404，虚拟机未运行。并非域名规则库、Root或DNS功能失败。

本次仅改固定历史 APNIC 资源路径到 `/stats/apnic/2026/delegated-apnic-20261116.gz`，解压后必须等于此前同源快照 SHA256 `f5bc4f8969b76afce7622820711e446db09da71c981cdf1f6cf49c3573fbc557`，否则构建立即 FAIL_CLOSED，不使用新一天数据、不降级样本CIDR。

新增真实内核DNS UDP/53验收：Root 子进程先 `CLONE_NEWNET` 且确认内核 namespace不同、`/proc/net/route` 初始为空，创建两条非持久 owned TUN（模拟 `physical`/`tunnel`）分别绑定 `198.51.100.1/30` 与 `198.18.253.1/30`，随后 **由同一版Android Rust CN geosite + UID policy** 选择 DNS 出口。对 `.cn`、`www.baidu.com`、普通域名、global CN域名、两种模式的WBD server-bootstrap 总计6种条件发送真实 UDP/53 DNS A question，读取对应物理/隧道TUN 上内核发送的IPv4包，注入 DNS 回包（同 Transaction ID，海外真实A=`8.8.8.8`），从UDP socket 收到完整响应；同步验证 CN域名海外A业务策略仍Tunnel。返回 `dns_udp_gate` 的逐项字节/出口/transaction/错误码，所有对象退出后fd关闭/私有ns消失、主Android路由不变。

此验证的两个 resolver 均是隔离命名空间的**合成DNS对端**，而非实际 `223.5.5.5` 或 `1.1.1.1`；不抓系统 Android DNS、没有真实WBD TLS和数据转发、不注册VpnService。Native只在App已保存且Root校验完整 geosite 后执行短时DNS测试；CLI若 `CLONE_NEWNET` 环境阻止则报告 `ENV_BLOCKED`，实际业务仍需生产 DNS listener/Android netd和 owned journal才能启用。

UI CI 在同一 App 真实触摸→私有配置→Root 读回链路基础上新增检查 `dns_udp_gate.status=SUPPORTED_IN_SCOPE`、6种收发正确、4个Direct与2个Tunnel、所有响应A地址为8.8.8.8，拒绝仅静态策略就报内核DNS PASS。未取得同SOURCE KSU Action PASS前此新项 **NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Fix immutable APNIC snapshot rotated URL with SHA256 enforcement; add real synthetic dual-egress UDP/53 kernel packet-and-response evidence under empty CLONE_NEWNET for CN DNS/global/server bootstrap, without Android netd Apply."}
```
