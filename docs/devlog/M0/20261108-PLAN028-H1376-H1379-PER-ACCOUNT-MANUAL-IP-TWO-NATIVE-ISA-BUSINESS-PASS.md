# PLAN028 H1376–H1379：两个原生架构的真实双账号手动 /32 TLS/Rust 产品业务完成

2026-11-08 并行真实 Go/TLS443 / Rust M4。Windows 原两个签名 Wintun OS 设备的隔离证据与 Linux 原双账号认证证据仍分别保存；不可合并成“Windows 两原产品客户端同服业务 PASS”。

## 真正完成

- [H1379 并行源锁定 Action 42459434353](https://github.com/lly8666/wbd-next/actions/runs/42459434353) **SUCCESS**，两个独立 Runner：Ubuntu x86_64 ELF62 与 Ubuntu ARM64 ELF183。原 Go donor `a7a82db...`，原 Go client、Go server 和 Rust M4 使用同一 overlay SOURCE `29f0c0f432ee8ce292910399be41077a4c838d37` 独立分别编译，所有包 SHA256 锁定。
- Alice/Bob 两个真实独立 protected credential 账号，手动给定唯一 `/32`：**10.66.0.2/32** 和 **10.66.0.3/32**，两端原真实内核 TUN OS MTU 各 **1389**。三次原 TLS443 会话：A 上线→A+B 同服并行→A 精确 Stop 而 B 真实 UDP 继续→A 原 TLS 再认证且 B 继续→新 A 精确 Stop→B 仍实际继续→B 与共享服务端 TUN 真 Stop。
- 每个平台原 Rust M4 服务器共享一个 TUN，**59** 个原 IPv4 UDP 应用 echo、最终 `routed=59, unrouted=0, backpressure=0, reader_joined=1`，全部客户端 `V4_PUBLIC_NATIVE_STOP_DRAINED` 与服务器 `V4_PUBLIC_SHARED_TUN_STOP_DRAINED`。**手动/32客户端使用私有 Rust TUN 读者**，不能要求其打印自动分配时的客户端共享读者标记。
- 服务端新 `--manual-client-leases-file` 由 0600 无软链接本地文件配置，与 `--users-file` 账户表一一对应，实际原 TLS 凭据验证 **先于**按账号选择服务端拥有的手动 `/32`；同租约、越界租约、缺失账号、零 tunnel ID、混用 auto pool 均拒绝。默认旧单例手动 tunnel ID 必须精确匹配。**不改 TLS/ Rust wire 报文，也不信任客户端自选服务器路由**。

## 原始误报与重验的字节级分账

- H1376 原始 [Action 42458575147](https://github.com/lly8666/wbd-next/actions/runs/42458575147) 早期 x86 因 fixture 固定 ARM 架构断言，ARM 因仍保留旧全局唯一 tunnel ID 校验而在产品认证前失败；这两项原失败**保留且不视为该 SOURCE 的业务 PASS**。H1378 [Action 42458826122](https://github.com/lly8666/wbd-next/actions/runs/42458826122) 是旧产品 SOURCE 的 x86 预验证，原 FAIL 同样保留。
- 修复认证后的按账号 tunnel ID 条件后，[Action 42459202785](https://github.com/lly8666/wbd-next/actions/runs/42459202785) 原始两平台已完成全部原客户端 59 UDP / 真 Stop，却在**结束后**因 fixture 错误要求手动客户端记录 `V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client` 红灯。两个原本 **FAIL** 归档各 6 文件 CRC 全 PASS：x86 ZIP SHA256 `f7eb635b1e675544cc8bfe27f51b2f4e7c8bce4f00d85664d59fdb90778d9317`，ARM ZIP SHA256 `e00947bc53af9c5bb6820578a9788a9500c9ce89499531f259ab58a9d6afcd20`；原始 app 日志和 server routed59/queue0 均存在。
- H1379 最终绿与上述红场景**各个平台的原 Go 客户端、Go 服务端、Rust so 三项二进制 SHA256 全部逐字节相同**。唯一修正结束条件：手动客户端验证 `V4_PUBLIC_NATIVE_STOP_DRAINED`，不要求 auto-shared-reader 标记。没有因为 CI 红而悄悄改产品业务。
- H1379 最终 x86 **7 文件 CRC 全 PASS**，ZIP SHA256 `bd3a5a8841110dc293b3f87a8de26ec84282d0c030a14823688756a3b0ee3a31`，Artifact 13608239527；ARM **7 文件 CRC 全 PASS**，ZIP SHA256 `0b5d57cc5d33b42b40ead2e29fc2d8113fd472ab8c356341a4965e3b24d7edd5`，Artifact 13608692410。
- 不可变验收：docs/evidence/M0/PLAN028-H1379-SOURCE29F0-X86-ARM64-REAL-TWO-AUTH-MANUAL-LEASES-UDP-STOP-PASS-20261108.json

## 下一硬门

Windows 原签名双 Wintun kernel UDP 和 Linux 原双账号 TLS/Rust now各有独立原生 PASS，但 Windows 两个实际**同时认证**的 Go TLS/Rust M4 客户端在同一个443 WSL2服务器、两独立 Wintun OS owner/WFP/WAL、A Stop 留 B UDP/TCP，仍 **NOT_RUN**。同连接热 MTU H998 老失败独立保留，L3 两条 1800s、Android/物理 WAN 未做。PLAN028 **IN_PROGRESS**。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Original Go TLS443/Rust M4 server now binds distinct manual /32 to protected verified principal; H1379 x86 and ARM64 independent original native real UDP+Stop PASS, with red reporter byte-identical binary proof. Windows dual authenticated product remains NOT_RUN."}
```
