# A44｜选中Chrome后不能浏览：真实业务TUN/RAW/回程与UID route-get

## 真机证据

用户Android API36 SOURCE `f82e3130d5b67f6732248dc89178089211562687` 137个固定事件，Normal/off选定应用UID两次启动：原Go FakeTCP/TLS（证书身份验证这两次关闭）/受保护Admission、真实/32 OS readback、原Rust native RAW/TUN M4、A43旧Go RX核过滤器、UID路由私表原Kernel读回皆成功；两次Stop也按原owned先撤UID、Rust Join、RST清理后ROOT EXIT0。Chrome实际浏览器**无法上网**，没有真实业务数据交付证据。Linux的同源Normal/off内网UDP Oracle不证明Linux服务器具备公网ip_forward、FORWARD规则、SNAT/MASQUERADE；Android系统DNS/netd物理绕行也未证明。

## 一批审到真实APP数据

现有原Rust单一M4 TUN readv→原M1/M3 AEAD封包→真实RAW sendto→原Rust反向AEAD→真实TUN写回链。A44在**这些原真实工作点**增加仅原子计数：`TUN_IPV4_SEEN`代表通过受保护/32源地址+原IPv4长度检查的内核读入；`TUN_IPV4_REJECTED`代表真实TUN入包被源/长度检查拒绝；`APP_RAW_TX_COPIED`代表原M3业务包实际被内核RAW发送复制（**不等于服务端收到**，Health帧不计入）；`APP_REVERSE_TUN_WRITTEN`代表原M4认证后向真实TUN写入。复用原 Rust TUN DNS53只读计数，事件`DNS_UDP53_TUN_SEEN`和`DNS_TCP53_TUN_SEEN`只表示同一原生TUN Worker观察到DNS，不证明系统Resolver/DNS hijack成功。原Rust新增小型只读FFI，原Go复用每秒Health监控、Stop前读最后一次，首次非0发固定`V4_PUBLIC_ANDROID_BUSINESS`；Java Service原白名单映射成脱敏TXT，不复制APP域名/UID/原始包/凭据，不增加第二reader、Go每包处理或新控制器。Linux服务器端也未改协议。

原selected-UID原内核journal实际安装成功后，另加**只读**`ip -4 route get 1.1.1.1 uid <selectedUID>`，至多8次，输出`ORIGINAL_GO_UID_ROUTE_GET_MATCHED_TUN`、`MISMATCH`或`UNAVAILABLE`。未改变kernel route/Stop；toybox不支持时只记UNAVAILABLE，不把无fwmark route-get判断成Chrome有特定fwmark真实访问成功。

## 下一份设备TXT能一次分出故障段

- `UID_ROUTE_GET_MISMATCH`/无`TUN_IPV4_SEEN`：检查真实Chrome socket UID、Android RPDB/fwmask、系统Resolver/IPv6，无权据此宣称Rust出站异常。
- 有`TUN_IPV4_REJECTED`、或有`TUN_IPV4_SEEN`但没`APP_RAW_TX_COPIED`：定位原Rust内层/32、MTU、AEAD/RAW发送。
- 有`APP_RAW_TX_COPIED`没`APP_REVERSE_TUN_WRITTEN`：核验原Linux server真实收到，server公网forward+NAT和回程。未经授权不操作用户实体服务器。
- 有`APP_REVERSE_TUN_WRITTEN`但Chrome仍不通：优先查系统DNS、Chrome Secure DNS/DoH、真实TCP/UDP握手和Android netd。

所有新增事件均是实际累计计数首次越0才报；不冒称Internet PASS。当前Chrome、DNS、服务器外网转发仍为NOT_PROVEN。本次复用原Linux Oracle、原ARM64签名APK和Java Host gate验收，不手工重型dispatch。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"真Android上M4/UID/Stop成功但Chrome无法浏览；A44补实际原Rust TUN/RAW/反向TUN及DNS53业务收据，selected UID只读真实route-get，隔离公网/NAT与netd原因。"}
```
