# B1 Android Root：原Go双上游 DNS UDP/TCP 真实线报文组件（2026-11-17）

唯一开发分支 `experiment/android-temp-root-probe`；源基线 `42b85e61a350ef8e5774bebf8e47246dbf8f5925`。保持 PR #36 Draft，不触 main/M0/实体KernelSU/任何额外云资源。

## 软件施工

- 原Go标准库新包 `r0/go_overlay/internal/v4productcli/dnsnative` 解析真实DNS QNAME、QTYPE、事务ID、EDNS OPT；每问仅选一个上游，没有FakeIP。内建两个唯一生产端点：物理中国DNS`223.5.5.5:53`和WBD隧道DNS`1.1.1.1:53`，无备用/竞速/跨方向失败回退；原WBD服务器bootstrap域名始终物理，普通开启CN域名分流时依注入CNMatch选择，关闭时普通DNS走隧道。
- UDP实线收发；仅当UDP应答TC位为1才在**同一个固定DNS endpoint和同一种物理/隧道Path**上执行TCP长度帧查询；错误ID/题名/类型/不完整/超限应答直接报错、不改用另一上游。边界请求4096B/回复16384B，缓存最多256个可验证正答，严格TTL过期、每次查询重写TXID；单航班合并最多64个独立待处理键，后台不轮询。
- 外部必须提供`DialFunc(ctx,Path,network,endpoint)`：未提供拒绝创建Resolver，无任何隐式`net.Dialer`或Android OS默认DNS出口。当前**没有实现实际Android NetworkHandle socket绑定、Rust/Go物理TUN真实DNS interception、系统netd Resolver接管、正式CN geosite数据匹配、内核分流规则和普通App DNS的UID还原**，不能宣称这些已完成。原Go TLS/M4及A8 route无改动。
- 新独立B1 Actions job用Go UDP/TCP loopback server**真实DNS wire测试**，覆盖QNAME、split关闭/bootstrap、UDP TC→同Path TCP、拒跨上游回退、错误ID/畸形查询、TTL缓存、并发合并；测试自监听ephemeral本机端口不是53。原ARM64 Bionic Go构建复制同SOURCE Go包并交叉编译Android ARM64 Go test ELF，不运行该ELF。原M3、Root APK和原Linux server oracle仍作为同SOURCE既有防回归门。
 
## 严格状态

本 SOURCE 初始代码只有实现，必须待 GitHub Actions 实测才能标DNS wire PASS。即使Host UDP/TCP wire PASS也只能记`B1_HOST_DNS_WIRE_PASS`，不是`ANDROID_SYSTEM_DNS_PASS`：Android16 ARM64 guest P2/P3因GitHub ARM64 host无KVM ENV_BLOCKED，Android双向WBD TLS+DNS/分流、真实App Resolver和KernelSU P5均NOT_RUN。不会触摸Android全局netd、默认路由、VPN/FakeIP或持久root系统服务。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B1单向绑定式原Go双端点DNS真实UDP/TCP wire、TC同端点回退、TTL缓存/并发有界及独立真实loopback Actions门；不宣称Android系统Resolver已接线。"}
```

## B1 本SOURCE Actions 真实验收结果

[Android ARM64原产品 Action #44069144804](https://github.com/lly8666/wbd-next/actions/runs/44069144804) SOURCE `8534a9182475a07072a4ae0e77807e23e6a3261f`：**6/6 Jobs SUCCESS**。独立`b1-dns-wire-loopback`执行真正Go loopback UDP/TCP responder，七组`TestOriginalQNameSelectsCNPhysicalOrTunnelWithoutFakeIP`、`TestSplitOffUsesTunnelBootstrapAlwaysPhysical`、`TestTruncatedUDPOnlyTCP53SameEndpointAndPath`、`TestRefuseCrossFallbackIfSelectedPathFails`、`TestRejectSpoofedTransactionAndMalformedQuestions`、`TestBoundedTTLCacheIDRewriteAndExpiration`、`TestConcurrentQueriesCoalesceWithoutBackgroundTimers`均PASS；打印`ANDROID_B1_DNS_WIRE_REAL_LOOPBACK_ONLY_PASS`，source-locked host receipt附Hash。原Go donor源锁及Android ARM64测试ELF交叉编译、原Go/Rust Bionic ELF、A8 rootjournal、原M3、独立签名Root APK与原Linux真TLS/租约/Rust M4双向UDP/Stop oracle均PASS。

ARM64 host准入结果仍`KVM_NOT_ACCESSIBLE arch aarch64 kvm NOT_AVAILABLE`，不启动Android userdebug guest。**B1资格是HOST_REAL_UDP_TCP_DNS_WIRE_PASS，不是ANDROID_SYSTEM_DNS_PASS**：正式App/原Go持续业务尚无DNS socket路径绑定、CN geosite真实数据、TUN包捕获、Android Resolver重定向/Root路由回读、TCP53真实运营网络、DoT/DoH/CLAT。故P2/P3与实体P5仍NOT_RUN。版本A8真实多UID路由原有代码未变。
