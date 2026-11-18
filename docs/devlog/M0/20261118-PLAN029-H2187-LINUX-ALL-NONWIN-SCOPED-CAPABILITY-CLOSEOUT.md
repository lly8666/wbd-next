# H2187｜PLAN029非Windows功能卡补测签名收口（Linux x86_64 + ARM64）

**用户提出的问题正确：H2177基础Linux 10/10并不能证明Game启动随机填充已在Linux客户端可用。** 后续H2181–2186沿原Rust GameAdapter/同Go TLS保护组真正把Linux Game2/4的off/tls/flows接入原每lane AEAD记录发送；在Linux真实AF_PACKET send成功时才计 `padded_records/padded_bytes`，并严格区分Linux不支持的Normal/Fixed/Auto填充。未把有静态参数或Rust预算测试当网络PASS。

## 本批真实结果

- 签名产品+夹具SOURCE `e174235872d32cca69bf921fb59904f9bcaee889`；[Action 44278039887](https://github.com/lly8666/wbd-next/actions/runs/44278039887) **completed SUCCESS**，两个独立原生作业分别 x86_64 `134711109425` 与 aarch64 `134711110000`；原ZIP [x86 artifact14415547592](https://github.com/lly8666/wbd-next/actions/runs/44278039887/artifacts/14415547592)、[ARM artifact14414634232](https://github.com/lly8666/wbd-next/actions/runs/44278039887/artifacts/14414634232) 已下载/检查整份原summary、各场原真实客户端与服务端Stop日志、kernel TCP/UDP app收据、SHA manifest及owner IPv6读回。每ISA**8/8**，合计**16/16 PASS_SCOPED**。同ISA八场使用一次原Go TLS+Rust native ISA-L构建；不同架构分二进制SHA，不能混当同一机器。
- 两架构每个均有 **六个独立Game随机填充原生场**：Game2 FEC off `off`、Game2 FEC off `tls`、Game2 FEC off `flows`（`outer-repair off`）、Game2 `fixed6+flows`、Game4 `fixed6+flows`（默认宽错峰）、Game4 FEC off `immediate+flows`（`outer-repair off`）；每场客户端和服务端各自原TLS认证、Rust每lane AEAD+PN、真实OS TUN→raw AF_PACKET发送、内核UDP与TCP**两个方向真实应用echo**、owned Stop+netns cleanup。
- **原raw M4成功复制的padding记录/字节（每个方向相同）**：x86_64的Game2 off `0/0`、tls `4/842`、flows `8/1971`、Game2 FEC6 flows `8/1058`、Game4 FEC6 flows `12/2996`、Game4 off immediate flows `16/3030`；aarch64对应`0/0`、`4/503`、`8/2494`、`8/2750`、`12/2954`、`16/4133`。每条 `<=500 B`。Game2 fixed6 FEC原parity各端 **96**实际M4 copy，Game4 fixed6各端 **96–97**；`recovered_candidate=0`，无造丢包修复效果。新Game payload只经原Rust `startup_source()`提取真正IPv4源，parity/health不加填充；TLS档本场真TCP应用数据前缀模拟TLS-record-shaped bytes，**不是完整应用TLS握手**。
- 其余**两场Normal/ISA**为真实Go客户端记录AES-128-GCM（默认外层1460）和AES-256-GCM（外层1280）。后者原TLS/Rust协商内层MTU真实OS读回**1209**、MSS1240，两个方向DF合法边界成功、+1 DF真内核拒绝，两个TUN无IPv6地址/路由，真实TCP+UDP应用双向echo，Rust每端 `tun_delivered=42` 和双Stop；外层1280引发内层1209低于IPv6最小1280，因此Linux per-device proc节点不出现是正常OS情形，本批定向增强夹具严格读MTU/零IPv6地址路由而非跳过检查。
- Game2/Game4 `outer-repair off` native Rust readback均 `repair_enabled=0 outer_data_retransmitted=0`，并且原始业务双向通；Game4默认wide原schedule `mode=2` 与显式immediate `mode=0` 读回真通过。所有这些结果均**没有受控丢包／性能因果资格**。

## 保留旧失败与未测边界

H2181根编译门Rust模块cfg FAIL、H2182纯FlowKey cfg FAIL、H2184无离线route-key请求X25519原Go服务端预TUN拒绝FAIL、H2185外层1280后旧sysctl裸查FAIL均原Action保存，不能擦除。新SOURCE只为**当前合法已有Linux产品功能**：Linux Normal/fec-fixed/fec-auto `--startup-padding tls/flows` 仍**NOT_WIRED且明确拒绝**；无离线route-key的Linux在线X25519引导仍**NOT_WIRED**；manual-IP真实物理MTU 1500→1280动态热切换未验/旧FAIL留存，后续需auto-ip/lease-pool/path-supervisor专用fixture。未独立测试持久轮换+新Game填充组合、Linux DNS/CN/WinForms/Wintun等Windows专属功能、不同ISA跨物理机互连、真实ARM板、全宿主IPv6、CPU/RSS/p99/长时间丢包、每个cipher×FEC全组合。完整PLAN029/029B技术出口仍**OPEN**，030未开始。

证据签名唯一入口：[H2186机器可读原生16场双ISA](../evidence/M0/PLAN029-H2186-LINUX-X86-ARM64-EIGHT-CROSSPLATFORM-NATIVE-PASS-20261118.json)，原Go pinned `a7a82db31fe736ffedee330795a3234d358f1984`，原native ISA-L pinned `c387163fcbca62701d646149564c550c78a4f985`；[H2186 maintenance 44278040054](https://github.com/lly8666/wbd-next/actions/runs/44278040054) SUCCESS。保留H2177另一SOURCE基础Linux 10/10证据，不能合并成当轮26/26同SOURCE。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding","record-crypto","game-fixed-fec","game4-copy-stagger","outer-opportunistic-repair","path-mtu-budget","linux-raw-tun","arm64-targets"],"reason":"Promote only H2186 same-SOURCE 16 native Linux x86_64/aarch64 scoped successful original Go TLS/Rust AF_PACKET Game padding/AEAD/FEC/copy/MTU/Stop tests and preserve unsupported/unrun boundaries. No product code change in docs-only closeout."}
```
