# H2181｜PLAN029可用非Windows功能盘点、Linux随机填充接线与互补原生试验

## 用户反馈核对

H2177 [Linux双ISA 10/10真业务签名](https://github.com/lly8666/wbd-next/actions/runs/44258876671)仅运行Normal/Fixed/Auto/Game2/Game4固定FEC默认冷模式和真实TCP/UDP、TUN/MTU/Stop；**没有实际启用或测量startup-padding off/tls/flows**。PLAN029随机填充非WinGUI独占：已有portable Rust策略20..30 records/2..3s、每record随机0..500B且限制物理MTU，但历史实际加密原Go→Rust接线只在Windows M1/Game M4。此前Linux CLI没有startup-padding选项，Linux GameAdapter原实现被编译时置零。因此未接线不能拿H2177原base网络PASS冒充随机填充PASS。

## 对功能卡的Linux可用性逐项判断（仅本轮选补的原生代表）

| 功能卡 | 原有Linux覆盖 | H2181互补动作 |
|---|---|---|
| `startup-flow-padding` | Rust策略单测；Linux原Game真实冷接线和业务未验 | **产品候选**：Game2/4受原Go TLS保护后调用Rust M4一次设置off/tls/flows；原raw AF_PACKET物理send成功后只读记录/字节计数。Game2无FEC off/tls/flows，Game2 fixed6 flows，Game4 fixed6/off flows；每场双端真实TCP/UDP、FEC parity不填、Stop。Linux Normal/Fixed/Auto 非off明确FAIL_CLOSED，不当作支持。 |
| `record-crypto` | H2177默认ChaCha，AES差异未独立当轮测 | Linux Normal分别客户端AES-128-GCM、AES-256-GCM原Go TLS认证+Rust真实双向TCP/UDP |
| `outer-opportunistic-repair` | default on，off分流未独立本源验 | Game2及Game4指定`--outer-repair off`且核真实outer回执不重发 |
| `game-fixed-fec` / `game-lanes` | H2177 Game4 fixed6、Game2 off | Game2 fixed6 flows／Game4 off flows补空缺组合、source/parity核内copy与AEAD鉴权 |
| `game4-copy-stagger` | H2177 Game4默认wide | Game4 immediate对照、真实选择与物理copy读回 |
| `tls-auth-multiclient` / `client-domain-bootstrap` | 凭据TLS本源H2177；Linux域名bootstrap未实现为Win原Npcap方案 | 路由密钥省略时原Go pre-TLS X25519且真TLS认证读回（非Linux域名引导） |
| `path-mtu-budget` / `linux-raw-tun` | 默认1460真实OS TUN/DF | 1280指定外MTU和1460→1280物理接口动态缩窄后真内核业务 |
| `original-lane-rotation-jitter` / `idle-rotation-keepalive` | 历史Linux source各自有真实限域/计时资格，H2177短测只测owned Stop | 本批不重复旧18秒±3秒长场；维持SOURCE隔离，未把本源新Game padding与轮换组合当PASS |
| `fec-auto`/`fec-fixed`, `native-crypto-backends`, `first-arrival-dedup`, `generation-stop`, `link-fragment-reassembly` | 各有Rust定向单测和H2177两架构真基础，未涵盖全部loss/回绕/片压/NEON指令因果 | 复用本源码Rust/Go单测＋本轮真业务，不伪称覆盖全状态空间 |
| `dns-split-ipv6`、`client-domain-bootstrap`、WinGUI等 | Windows客户端业务/配置特有；Linux仅original TUN IPv6-off | Linux没有CN/Direct/FakeIP/Wintun/WinForms；不造不存在的Linux实现/测量 |
| `server-management-cli` | PLAN030，仅PLANNED | 不启030 |

**新Linux Game接线策略：**复用既有Rust `TunnelStartupPadding` 与GameAdapter原protected per-lane seal；只有真IP/TCP/UDP源数据或GameFEC typed source可消耗，Parity/Health不消耗；先由原Go TLS鉴权的Game组设置，再用raw M4`send_one`成功条件累计有额外pad的record与bytes；off零且不动PRNG；不能由COLD前FakeTCP未认证宣告。只用原原始record AEAD/PN，没有第二加密栈或Go逐包修改。用户外层MTU与物理接口MTU取较小后限定pad，不触及宿主全局IPv6。严守本SOURCE原native出错必须留第一失败。

**效率：**两个真正原生`ubuntu-24.04` x86_64/`ubuntu-24.04-arm` aarch64并行；各只构建原Go TLS两个CLI+Rust/ISA-L一次，原脚本每场双netns由真实内核普通TCP/UDP+双Stop，8个互补短场串行首错退出；不重复旧H2177基础5模式及Windows H2169六场。在Linux Normal/FEC no-padding处有明确`NOT_WIRED`验证，不忽略配置产生假PASS。

实施/构建阶段的功能资格只为`IMPLEMENTED_NOT_TESTED`；直到原NativeAction completed SUCCESS和同SHA受控raw copy stats签名后方能提升。正式028既有FAIL保留、PLAN029/029B全技术OPEN、PLAN030未开启。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"Implement exact original authenticated Rust Game2/4 native Linux startup padding cold mode and raw AF_PACKET successful-copy receipts, keep unimplemented Normal/FEC selector fail-closed; stage source-locked dual-native cross-platform trials, do not promote until real Action results."}
```
