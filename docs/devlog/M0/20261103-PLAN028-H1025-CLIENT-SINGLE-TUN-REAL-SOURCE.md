# H1025｜PLAN028真Linux客户端进程唯一Rust物理TUN读者、受保护/32默认路由owner

## 现有真实资格、原失败边界

H1024 SOURCE `09cbc73d326e74d34db6da310630345e96c0cf3c` Action `41593787277` / native job `125776303834` **SUCCESS**。五个真实Linux netns：Alice两个不同安装ID与Bob另一账号，3个实际原Go TLS分配且OS安装的不同/32，第四个Alice同安装的新TLS incarnation由另一underlay五元组在线接管旧Alice；一个server443和唯一Rust服务端TUN reader，应用真正UDP `routed=70 unrouted=0 backpressure=0`，所有Original Rust M1/M4 Stop成功；保留并发/交接及另一设备业务证据 `docs/evidence/M0/PLAN028-H1024-SOURCE09CB-THREE-INSTALLATIONS-ONE-RUST-TUN-NATIVE-20261103.json`。同源1% Linux netem `offered=512 delivered=507 missing=5`，Fixed/Auto各64 UDP短样和Game2/Game4短native实测有限域PASS。H1024 Governance及Feature Catalog两job成功。**这些客户端在不同进程/不同TUN内**，不能声称同一个客户端进程里两Rust generation不抢读同一个TUN；这就是本H1025必须先处理的资源约束。

## 产品代码——复用原Rust共享reader而非第三套恢复/热循环

1. `crates/wbd-engine/src/v4_embedded_go.rs`的**现有一个进程级Rust SharedTunReader**增强为按角色选择：服务端仍用已验证的客户端`/32`作O(1)目标路由；客户端绑定**保留0.0.0.0 key**作唯一已认证默认发包generation，目标可以是任意VPN/LAN IPv4，不增加稳态字段或新控制/转发协议。新客户端generation必须完成真实原Go TLS、Rust commit/配置并启动M4 worker才发布覆盖默认路由；旧A的`alive=false`后不许继续分配或转发新TUN业务，旧Stop仍用generation+Arc精确栅栏清理，不能删除新B。默认只作为客户端内部owner key；服务端已分配/32严禁0.0.0.0，互不混用。
2. 原`wbd_m0_embedded_go_bind_authenticated_client_ipv4` ABI复用：服务端继续对实际TLS租约进行Rust M4解密后inner IPv4源IP校验；客户端只在原Go保护TLS获得冻结`AuthenticatedLeaseIPv4`，**Linux OS真正安装/读回**相同/32后，才允许把该session的原Rust generation标为可绑定共享reader的已认证本机租约，仍是私有原Go冷控制C ABI。未认证/手动IP、已启动/已绑定、Game合组后迟绑均拒绝。
3. `r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go`给真正客户端产品配置新增`SharedTun`，只在AutoLease保护TLS和OS读回成功后调用原Go→Rust绑定，且在原Rust M4 workers启动前完成。原server产品原样仍使用其已通过的相同ABI；旧manual客户端/Game原有路径不自动采用。
4. `r0/go_overlay/internal/v4productcli/linux.go`的Client Run仅在Normal自动租约模式开启**一个进程级Rust reader**，复用整个原TUN生命周期而不是每次重认证重开；各session继续只有现存原Rust M1/M3/M4。Go `Run`改具名error返回以确保**Rust reader Close/join失败不能仅记日志而假装退出成功**；client shared.Stop始终先于原OS TUN Close。无Go per-packet热路径、定时控制器、第二套AEAD/FEC/重传、窗口扩容。
5. 原真实Linux双netns自动/32 TLS测试除服务端单reader `routed>=5`，现在强制验证**客户端另一个进程自己的唯一shared reader `routed>=5`**、客户端Stop和reader joined，打印`M0_PLAN028_REAL_CLIENT_PROTECTED_DEFAULT_SINGLE_TUN_READER_PASS`。现有五netns同账号双安装+Bob加换代测试再要求四个真正Go客户端全部 reader Stop/join，仍要70真正TUN UDP/单server443。Rust同Source纯单测证实默认路由多任意目的、generation A→B覆盖、旧Stop不能删B。
6. `.github/workflows/m0-plan012-combined-functional.yml`保留源锁**一套原Rust Release + 原Go两端真实可执行文件**，同源Rust unit/default及Linux真实netns两项强门；后续1%/FEC/Game旧回归继续。不借用H1024 PASS替代本SOURCE结果，不用只看静态导出符号的假验证。更新原`tls-auth-multiclient`与`idle-rotation-keepalive`两功能卡，保留前源证据、H998历史FAIL及Android/物理限制。

## 下一步真实未完成部分

**H1025当前`IMPLEMENTED_NOT_TESTED`，不得在新SOURCE Actions确认前标原生客户端单reader PASS。** 此提交解决同一客户端进程未来A+B物理TUN争读的底层唯一owner，但`Run`仍一次只运行一个`runClient`；尚未提交原生Linux rtnetlink/Windows OS网络通知、200ms/500ms事件合并、真实新underlay接口/源IP重新绑定、持有A同时启动同进程B、per-client双向MTU安装读回和7种模式共同交接。只有真正新SYN/TLS/Rust客户端owner后才可升级这些资格。H998物理MTU1500→1280小包缺失及ARM64 Game4FEC、Win Game4 lane2 bootstrap旧FAIL保持原判定。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","idle-rotation-keepalive"],"reason":"Real client process now uses the original Rust process-shared single TUN reader, authenticated OS-installed /32 default owner and exact generation handoff fence, so client new generations cannot race destructive TUN reads; actual Linux Go TLS/Rust 2/5-netns native gates added, not yet source-tested."}
```
