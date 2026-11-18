# H2197｜Linux 服务端五模式随机启动填充：双向独立长度流

## 当前状态：源码候选，真网 NOT_RUN

用户要求Linux服务器和客户端一样，各模式同时生效。核现有原Go TLS→Rust M1/M4原AF_PACKET产品：Linux服务器单例 Normal/off 和 Fixed/Auto 走 `V4LinuxServerProduct`，shared受保护per-client Normal的模式由TLS验证策略决定；Game2/4及共享Game group走 `V4LinuxGameProduct`。所有产品冷配置已有 `StartupPaddingMode/OuterIPMTU`；非off成功发送后有各角色自己的Rust内核复制回执。旧SOURCE [H2186](https://github.com/lly8666/wbd-next/actions/runs/44278039887) Game、[H2193](https://github.com/lly8666/wbd-next/actions/runs/44290120683) Normal及[H2195](https://github.com/lly8666/wbd-next/actions/runs/44292569034) Fixed/Auto各自原生PASS_SCOPED，不能跨SOURCE直接替新二进制验收。

发现相同认证epoch派生的Normal/FEC Padding PRNG 在client和server同流量上可能同序列。H2197仅在Rust **padding策略seed** 混入固定角色分离盐，Game使用独立角色盐作用于传给随机策略的本地epoch副本。绝不改 TLS protected epoch、KDF、AEAD、PN、record kind、FEC block/index/revision、原始IPv4、parity/repair、Game lane。默认off没有流状态；tls只筛合法TCP TLS-shaped前缀、flows筛已认证IPv4 TCP/UDP流，头部不合规不填；每流20–30条/2–3秒、每记录0–500B且真实MTU余量上限。客户端与服务器可独立设置同三档，均仅可由原Rust成功raw AF_PACKET复制累计。

全新隔离原生测试候选：每ISA一个source-locked原Go+Rust/ISA-L bundle，Normal、Fixed、Auto、Game2、Game4 × tls/flows = **10场/ISA，20场真实客户端+服务端**，每场严格要求双方各自`padded_records>0`和`padded_bytes>0`、真实双向kernel TCP/UDP echo、owned TUN IPv6与MTU、DF边界、Rust/Go owned Stop、netns清理；FEC仅kind2 source可填，parity kind3不填；Game按原lane FEC正确源分类。真原生结果只能认冻结SOURCE Action产物，当前H2197 **NOT_RUN**，不重跑历史已签名场次。

服务端缺少离线route-key的在线X25519前置交换继续按TLS契约本地拒绝；混合shared服务端单独auto-IP /32业务与物理动态MTU重认证仍需专用独立两端夹具；实体ARM板、跨ISA物理互联、真实应用TLS握手与CPU/p99仍NOT_RUN。029日常限域PASS但技术未收口；030不启动。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2197 Linux original server/client role-separated startup padding seed for Normal/FEC/Game and exact five-mode×tls/flows native source-locked validation candidate (NOT_RUN until Action)."}
```
