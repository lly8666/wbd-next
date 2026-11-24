# Android16 KSU 真正普通 App ↔ Root TUN 双向 UDP 实测收口

## 决策

**FUNCTIONAL_PASS，仅限一次性 Android16/API36 x86_64 KernelSU v3.3.1 模拟器。** 普通非特权 Android Activity（UID10218，untrusted_app，targetSdk37，INTERNET 权限）用 DatagramSocket 发随机 nonce UDP；获官方 KernelSU Manager 单独授权的 su 子进程（UID0，u:r:ksu:s0）在 Android 主网络命名空间建立单一 UID+目的地址 /32 临时策略规则和非持久 TUN。Root 真实 TUN 读取 App 发出的 UDP，然后向 TUN 写合法 IPv4/UDP 回复，**同一普通 App Socket 收到并校验对应 nonce 回复**。无 adb-root 冒充、假 su、降级 targetSdk、VpnService 或直接编辑 KSU allowlist。

- 成功 SOURCE：`e7d59cf7574d9932a9a24b3b273bb4e5106723b0`，[GitHub Actions 43823818642](https://github.com/lly8666/wbd-next/actions/runs/43823818642) **SUCCESS**。
- 原始 artifact **14205657446** ZIP SHA256：`2705d0863a0a740cdd7293b3e72864ffa3e0808082364dbc18d689fb0a3671cd`。实际独立下载ZIP校验一致，含84个文件。
- Root 进程单次 x86_64 NDK 构建 binary SHA256：`fced8a1bb3b0064d18963bb6e13f1d3580ee7eb87a71a6e1d1b38d9e5e1b0249`，SOURCE 与 APK/CI 同一提交；x86_64实际运行，ARM64 运行 NOT_RUN。
- App 私有 `appflow/app-flow.json` SHA256：`4e5c8f4378e2be7c0977ec4468d5aec60991f56232118cec212ca062535c4cbb`；host `appflow/summary.json` SHA256：`b228293e9191384c053de89020f507cf8f360aa6ebba2806133b9769b1509185`。

## 真实网络行为

| Gate | 实测 |
|---|---|
| KSU 管理器 | 官方 Manager 对精确包 `org.wbdnext.rootprobe` 的 Root 授权；普通 App 调用 `su -c` exit 0，子进程 UID0（KSU 域） |
| 普通 App 发包 | `wbd-app-<nonce>` 长40B，真实 DatagramSocket 发往198.18.254.2:49492；TUN捕获完整IP/UDP **68B**，源198.18.253.1 |
| Root TUN 回注 | 构造合法 IPv4+UDP校验和，以198.18.253.2:49492向App实际源端口回注 **70B** IP/UDP |
| 普通 App 收包 | 原来的 DatagramSocket.receive() 实际返回 **42B** 匹配 `wbd-reply-<nonce>`，源198.18.253.2:49492 |
| 有限路由 | UIDrange 10218-10218、目的198.18.254.2/32、优先级8200、table235，自有TUN MTU1400；不改默认/main路由 |
| 清理 | owned临时路由与规则删除、非持久TUN关闭后接口消失；Root内和CI宿主校验的Android全部IPv4 rule/route前后**逐字相同** |
| 状态 | `APP_UID_TUN_ROUNDTRIP_PASS`，su exit0，828ms为该次记录值、不代表性能承诺 |

### 失败及源码差异原样保留

单向 SOURCE `fbfe544c19f264b97f17f0dd8950b4f1b3d676f5`，[Action43823013289](https://github.com/lly8666/wbd-next/actions/runs/43823013289) SUCCESS：普通App实际68B UDP进TUN，清理通过，但**未要求收到回包**，不能当作双向成功。artifact14205471903 ZIP SHA256 `a0d91a16814d8919acbdb502fad9c7496931840764724389d341baf995d01033`。

首个双向 SOURCE `4eae26c3a99ac41feebe15a4565ff73ead337ea3`，[Action43823711435](https://github.com/lly8666/wbd-next/actions/runs/43823711435) **CI FAIL**：实际上 App JSON 已收到回复、TUN已注入70B，但 CI 还错误期待旧状态字符串 `APP_UID_TUN_FLOW_PASS`，所以不得重写原 CI FAIL。当前成功 SOURCE 调整验收为 `APP_UID_TUN_ROUNDTRIP_PASS` 并完整重测，得到真正 CI SUCCESS。

### 严格边界

这条规则**临时写在一次性 AVD 的主网络命名空间**，不是完全无系统状态修改。源码在确认 emulator、KSU UID0、规则/表无冲突后只添加精确 App UID+单个合成目的地址路由；正常退出 RAII 清理和系统前后快照验证。SIGKILL 后的残余路由恢复仍 **NOT_RUN**，不可直接作为生产后台 Root 服务。

正式 WBD Android客户端、Android netd/移动底层网络选择、NAT/conntrack、Wi-Fi热点/USB共享、DNS、IPv6/CLAT、FGS、真实蜂窝连接、真机ARM64/OEM、电源与异常重启仍未验证。主线/M0和手机 boot/system/SELinux 未改。结论仅为普通 App↔KSU Root TUN 双向数据面已经在指定模拟器**真实跑通**。

[机器可读SOURCE矩阵](20261116-ksu-appflow-matrix.json)记录每个证据与限制。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Record source-locked ordinary App UDP 68B -> real KSU-owned TUN, 70B reply injection and 42B App receive, with exact UID /32 policy and complete route restore; keep netd/NAT/OEM NOT_RUN."}
```
