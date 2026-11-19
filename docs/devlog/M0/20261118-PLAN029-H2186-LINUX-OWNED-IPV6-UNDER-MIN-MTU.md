# H2186｜Linux H2185 outer1280 真MTU1209被IPv6接口sysctl夹具假设误拒

## 上一轮实网证据，保留失败

[原生x86_64/aarch64 Action44269773178](https://github.com/lly8666/wbd-next/actions/runs/44269773178)，SOURCE `17cbbd8712ca886fe2c0546ddcd9b1bdebd74227`，两架构各7/8场原Go TLS/Rust真实双端PASS（Game2/4的random startup padding off/tls/flows+GameFEC fixed6/outer off/Game4 immediate，加Normal AES128）。第8 `normal-aes256-mtu1280` 两ISA同一检查失败，不改写Action整体FAIL。

精确原ZIP：[x86 artifact14410744904](https://github.com/lly8666/wbd-next/actions/runs/44269773178/artifacts/14410744904)，[ARM64 artifact14411254759](https://github.com/lly8666/wbd-next/actions/runs/44269773178/artifacts/14411254759)。本场两原始Go TLS/Rust正常Ready，真实双向ping各3/3，真实MTU预算记录 `outer_config=1280,advertised_mss=1240,tun_mtu=1209`，MTU边界两方向内层1209、合法DF包回显、+1 DF超限本地拒绝；两端Rust均 `link_completed=30 tun_delivered=30`，且两个原始 `V4_PUBLIC_NATIVE_STOP_DRAINED` 都成功。失败出现在接着运行的脚本 `cat /proc/sys/net/ipv6/conf/wbdcl/disable_ipv6`：Linux内层TUN MTU1209低于IPv6的最小1280，原runner没有对应每接口IPv6 sysctl节点。**第8场后续真正kernel app TCP/UDP未执行，不可宣称AES256整场PASS。**

## H2186唯一修改：按原OS接口读回解释IPv6状态

在原 `tools/arm64_linux_netns_smoke.sh` 的两个owned TUN检查上，先以 `ip -j -n <ns> link show <tun>` 读真实MTU，再检查每接口 `/proc/sys/net/ipv6/conf/<tun>/disable_ipv6`：存在则必须为1；缺失仅当 **real TUN MTU <1280** 才允许。两种情况都再检查 `ip -6 -o addr show dev <tun>` 与 `ip -6 route show dev <tun>`，必须0条IPv6地址/路由；MTU>=1280但sysctl缺失、sysctl=0、出现任何IPv6地址/路由均立即FAIL。各端留下 `owned-ipv6.txt` 真实readback。

原H2181补测Python runner在逐场原kernel TCP/UDP之前读取两端上述原物理/OS读回；校验每端唯一、满足低MTU条件、第8外层1280必须推导内层<1280。静态防回归固定判定门。保持源锁/同二进制SHA、真实原Go TLS→Rust AEAD、FEC parity只source填充、业务双向TCP/UDP、外层MTU/DF边界、两端Stop及清网强门；本轮仅修实测夹具，不触及Go/Rust产品代码，不复活旧全矩阵。

**边界：**Linux Game2/4 random padding可用候选仍待H2186全8×2完整签名PASS；Linux Normal/Fixed/Auto`tls/flows`未接线且冷配置显式拒绝；无预共享route-key的Linux X25519在线引导NOT_WIRED；手动IP动态物理MTU切换未验且旧FAIL保留。物理ARM、跨ISA独立设备/Windows GUI/DNS/Direct不在本批，PLAN029技术OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Only correct Linux dual-ISA native test-owned IPv6 procfs readback when authenticated outer1280 derives real inner TUN MTU1209 below IPv6 min1280; require no IPv6 address/routes and reject missing sysctl on >=1280. No product or API change."}
```
