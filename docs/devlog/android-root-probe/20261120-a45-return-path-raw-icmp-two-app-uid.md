# A45｜A44真机原Rust已发业务、无反向TUN：抓真实RAW收包及ICMP

用户Android API36 SOURCE `8da73ff0428291b006b28f762cf18ea9122d4784` 两次真实 Normal/off/selected UID（固定事件144条）证明受保护FakeTCP/TLS/Admission/32、原Rust RAW/TUN M4、GO RX新BPF、UID private-table`route get`命中、真实`TUN_IPV4_SEEN`和`APP_RAW_TX_COPIED`，首次还观察到`DNS_UDP53_TUN_SEEN`。两次均无`APP_REVERSE_TUN_WRITTEN`；Stop都完整且exit0。真实手机内核发出数据只意味着本机成功复制RAW，不等于服务器接收或成功转发。用户用另一个ping软件无法ping`10.66.0.1`，但收据`ROUTE_SCOPE_SELECTED_APPS_IPV4`不含选择的包名/UID：**如果只有Chrome被选中，其他软件的ping不经代理，这个失败不能直接证明原Rust ICMP回程**。也不擅自认定10.66.0.1就是当前服务器内侧TUN地址，须与实际server配置核对。

## 选择下一步：保持selected App组而不是全局

下一次用户可在UI选择Chrome和ping工具两项普通App（已有2..8UID组journal支持），Normal/off，先ping实际已核对的Linux服务端TUN内侧地址（可能为10.66.0.1，不能猜），再在Chrome走真实IPv4 TCP。全局模式会增添20用户/系统差异、throw/32出口排除、DNS/netd和Root manager UID的额外变量，不能解决已经有C2S RAW发送而没有证明S2C回包的问题；本轮不切。

## A45原生可观察的真实分界点

在**现有唯一原Rust M4**的RAW socket事件与解码位置增加仅Atomic可读计数，新增固定安全TXT：
- `RAW_SOCKET_READABLE`：实际内核poll该RAW FD可读，不是收到合法WBD包。
- `RAW_PARSE_FAILED`：原Rust调用原TCP解析后返回Err，不伪造AEAD认证。
- `RAW_PARSED`：真实接收包通过原IPv4/TCP绑定/校验，未证明M3/PN。
- `RAW_AUTHENTICATED`：原M3解包报告真实已认证link或Health记录。
- `RAW_AUTH_REJECTED`：真实M3报告rejected/malformed/discarded。
- `REVERSE_TUN_WRITE_FAILED`：真实原Rust回写TUN失败。
- `TUN_ICMP_SEEN`、`TUN_TCP_SEEN`、`TUN_UDP_SEEN`：仅对真实TUN读取、/32源和IPv4长度检查通过的内层IP按原协议号分类。ICMP只表示请求进入Rust，不代表服务器返回echo。
以上全部由只读新Rust FFI供原Go已经存在的1Hz Health monitor和最终Stop前查询，只有真实累计首次大于0才让Java固定白名单记录；不包含UID、真实IP、DNS域名、凭据、端口、时间戳以外的payload。无Go/Java逐包回调、无更改服务器TLS/协议/路由/crypto、无新增网络发包、无二reader或伪造SUCCESS。Linux原服务端共享M4代码行为保持不变，原测试与ARM64真实编译验证新增ABI。

## 后续分流

- 有`TUN_ICMP_SEEN`+RAW_TX但`RAW_SOCKET_READABLE`缺失：查真实Linux server的SYN之后M4 RX，TUN地址/路由，服务端是否产生echo；Android物理链路返回及其SOCK_RAW BPF。待服务端两侧真实包头/计数；不能因零事件就判定server丢包。
- `RAW_SOCKET_READABLE`而`RAW_PARSE_FAILED`或无`RAW_PARSED`：检查Bionic raw TCP包和原TCP parser/seq/MTU。
- `RAW_PARSED`无`RAW_AUTHENTICATED`或有`RAW_AUTH_REJECTED`：检查两端Go→Rust handoff seq/PN、密钥与AEAD原不变量，不关闭验证。
- `RAW_AUTHENTICATED`无`APP_REVERSE_TUN_WRITTEN`，尤其`REVERSE_TUN_WRITE_FAILED`：查原Rust重组/租约IP方向和真正TUN写回。
- `APP_REVERSE_TUN_WRITTEN`但ping/Chrome不通：区分服务端ICMP reply、DNS/DoH、TCP/UDP、实际APP UID。
Linux原服务端公网IP forwarding、FORWARD防火墙、NAT与DNS真实E2E仍未验证。无远程服务器/手机操作。无物理PASS宣称。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A44真机UID/TUN/Rust RAW TX均PASS但无反向证据；A45一次性RAW内核可读/解析/M3认证/TUN写失败与selected UID ICMP/TCP/UDP真实原生收据，避免贸然切全局。"}
```
