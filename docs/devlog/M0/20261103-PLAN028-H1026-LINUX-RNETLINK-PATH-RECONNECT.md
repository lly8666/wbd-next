# H1026｜PLAN028 Linux 真OS rtnetlink变化→原Go TLS/Rust同进程 A→A+B→B：完整工作包源码候选

## H1025源锁真实进度

截至此包起点 `main 7037f6eea30c532d4c8980071ec7514e62933968`：真实 Linux 原GoTLS自动/32客户端**进程唯一Rust TUN reader**、客户端5包UDP/Stop及服务端单reader都在 `41595536395` native Action成功；五真实netns三安装身份（三个不同/32、Alice两个安装+Bob其他账号）加同安装旧A→新R一次代际接管，总真实UDP70、server一个443和正确Stop PASS。对应新证据 `docs/evidence/M0/PLAN028-H1025-SOURCE7037-CLIENT-RUST-SINGLE-TUN-NATIVE-20261103.json`。Governance/Feature Catalog同SOURCE `41595536456` 成功。原 Win↔Linux Game4 lane2工作流 `41595536423` verify native部分FAIL，不能被Linux成功覆盖；H998物理1500→1280小包3/3及ARM64 Game4FEC Action失败仍保留。

## H1026完整Linux Normal Auto冷切网工作包

不是泛化新框架，不改变原加密、FEC、记录、稳态头、租约或Rust唯一TUN读者：

1. `r0/go_overlay/internal/v4productcli/path_linux.go`：真正订阅Linux `NETLINK_ROUTE` 的 LINK/IPV4_IFADDR/IPV4_ROUTE multicast。以**最后通知静默200ms、首通知绝对上界500ms**聚合；每批只重读一次 `ip -j -4 route get <numeric server IP>`，再核验selected源地址确实安装在有效物理接口，绑定ifindex、MTU与gateway快照。TUN自身网络更改/无关通知/快切A→B→A后有效快照相同均不重连；无物理出口则保持当前可用owner，不伪造ready。监听者只在冷OS层事件唤醒，无额外per-packet/周期keepalive或测速协议。
2. `path_supervisor_linux.go`：在真实 Linux Normal自动/32客户端原始 `Run` 上接线。以至多一个current原Rust owner、一个尚未通过原TLS的candidate和一个已发Stop的retiring instance复用原Rust共享TUN进程默认路由。变网后真实新源IP/interface/ifindex/端口、新路径MSS/MTU Rust预算 → 原Go SYN/保护TLS/原Rust M4就绪/数据内核filter完成 → 发READY → 精确取消旧A并等待原Rust Stop；B失败旧A保持健康，1–30s限界重试；通知不会跨过TLS或直接切指针。旧candidate若被新OS路径超越先取消并等其资源回收；重复事件不构建多套TLS。新会话严格保留安装ID、已认证server租约/32，拒绝活动A期间改租约；客户端TUN物理唯一reader不变。更大新路径在重叠期不放宽旧A预算；更窄新路径在B开始业务前按现有Rust预算修改并内核读回MTU。
3. `linux.go`直接启动上述路径监督器，不再要求Rust90s死亡或TUN上新payload才创建B；`runClient`只增加**原成功M4之后**不可伪造的ready回调，业务仍走原Rust。手动IP/服务端/Game旧模式原循环不受这个Normal auto-only冷回连改动。
4. `path_linux_test.go`检验路由JSON物理authority拒TUN伪路由、所有原rtnetlink事件类型、重复事件200ms/500ms绝对截止和无意义事件不触发。
5. **真实内核夹具**：给已验证的原两真实Linux netns产品增加`WBD_V4_PUBLIC_AUTO_IP=1 WBD_V4_PUBLIC_PATH_SWITCH=1`有界场景：原源码Go TLS客户端启动、原/32首5 UDP真实回显；真实 `ip addr add` 第二underlay源IP、真实 `ip link mtu 1280`及到server的`ip route replace src`触发内核通知；同一原Go进程和同一Rust共享TUN上的新TLS generation2必须READY、old generation1精确Stop、server source445的原session接管，然后相同VPN/32继续5 UDP回显。读取真正新内核route和TUN MTU、共享Rust reader`routed>=10`与最终两个端Stop。没有合成event、测试证书也不等于真实借站证书、没有借道旧Test runner fake TLS。原2/5netns及Fixed/Auto/Game/1%真实回归复用**一次**本SOURCE的release Go/Rust产物。
6. 复制/装配清单在`tools/arm64_public_go_rust_bundle.sh`和原Native GitHub workflow中同批安装新增Go文件及测试；新增workflow步骤只选一条物理source+MTU切换，不复制整个七模式×弱网测试矩阵。

## 严格不宣称与后续

本笔是**H1026新SOURCE候选，测试未运行时必须记IMPLEMENTED_NOT_TESTED**；尤其本次Linux 1500→1280是隔离netns上的接口/源IP/MTU真实change，**不能**覆盖H998真实物理路由1500→1280小包缺失3/3的失败。Linux新路径通知的500ms是冷通知合并预算，不是TLS跨网络的全部恢复SLA。Windows `NotifyRouteChange2`/interface源绑定、Game2/4逐lane和Normal fixed/auto七模式最高FEC切网、每client实时不同加密/FEC配置、DNS/route-key首次ClientHello、CPU/p99容量因果以及Android保持未完成。若本SOURCE CI编译/真实OS场景FAIL，精确修复真实源错误，不把之前H1025成功直接当成H1026 PASS。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","idle-rotation-keepalive"],"reason":"PLAN028 real Linux rtnetlink 200ms/500ms physical route/source/MTU notifications now trigger original protected TLS/Rust in-process Normal auto-/32 A+B→B with exact Stop and native two-netns app test; H1025 source-locked Rust client shared TUN evidence registered."}
```
