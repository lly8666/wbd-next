# H2212｜Linux双端真实短RouteKey、非WBD TLS混流、独立容量限额

用户要求M0完成Linux客户端前轮NOT_RUN的实际接入测试，并回答普通非WBD访客是否占WBD名额。旧H2209/H2210只有标准库TLS Go夹具、Linux Rust+Go服务端编译、RouteKey本地单测PASS；旧H2211 ARM64原Go双端BUILD_PASS，不等于新功能真实联网。本批严禁复刷旧弱网矩阵并不得跨SOURCE声明PASS。

静态容量：Rust原生16为lane/owner槽位、Game2/4按2/4消费；FakeTCP预认证冷表32，同端口非WBD普通TLS访客仅进P2 `FallbackFromHello`，没有Rust epoch/lease。H2212每实例增8个非WBD并发转发槽，未识别ClientHello才非阻塞申请，结束释放、满时普通流拒绝且零拨号，WBD识别TLS完全绕过；混合冷队列仅启用Decoy时16→24，native16和cold32不改。限制保护Rust数据面，却不承诺32恶意SYN不会挤占冷表；不凭硬编码推断吞吐或真实16人稳定在线。

真Linux客户端场景：在GitHub Actions两个独立原生ISA（x86_64/ARM64）复用已有生产双端Go/Rust ISA-L构建和成熟Linux netns/AF_PACKET/TUN/UDP/Stop夹具；源锁双端使用同一个0600随机32位ASCII短RouteKey文件，各有独立持久32B v2缓存；先真实TLS成功、Rust owner接管、TUN内层UDP Echo，再同时用独立Python标准库TLS1.3流从相同server443抵达loopback origin8443、交换ping/pong，验证普通访客不增加WBD Ready和Decoy额度8；Stop真实排干。在相同Runner再次从零启动server/client，验证缓存mtime_ns不变、同场真网和Stop重复PASS。Go附加额度满普通访客拒绝及受保护WBD零Decoy拨号测试。只有跑完同SOURCE工作流才记PASS。

保留边界：公网网关NAT真实DNAT、16个WBD满额压力、移动JNI/Android和OpenWrt实机均NOT_RUN；029/029B完整技术出口OPEN、030未开。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H2212 split ordinary TLS decoy limit max8 from authenticated Rust16 owner capacity; true Linux x86/ARM short RouteKey and persisted-cache two-start TLS/UDP/Stop plus same-port plain TLS decoy tests."}
```

## H2212 首次 x86/ARM 真实测试事实（失败不抹除）

SOURCE `9ffec3de81a3375d5088d1a546a3c994b7b483cc` 的 [Action44440706601](https://github.com/lly8666/wbd-next/actions/runs/44440706601) x86_64、ARM64两个真实原Go＋Rust ISA-L双端构建均完成，两个受限 netns Linux客户端服务端实际短RouteKey v2 TLS握手、WBD Rust M4和/32租约READY均发生。新业务测试在随后的普通TLS/缓存断言脚本报错，两个矩阵任务**FAIL**，不是业务收发和Stop PASS，不能跨源归纳成功。首轮工作流错误过滤遗失了独立普通TLS/python文件的traceback首因；本次只给H2212 opt-in脚本补脱敏普通TLS/loopback端点错误输出和阶段标记，**不改原握手、Rust、信令和容量限额代码**。后续按同SOURCE新Action修正唯一首异常并重跑2启动，不重派原旧矩阵。

## H2212 真实混流已通过、0600权限校验夹具修正

SOURCE `f5c7d95f2a002e5570f6e72dfcbde9d0e6c8b821` [Action44441506563](https://github.com/lly8666/wbd-next/actions/runs/44441506563) **两个ISA完整Action仍FAIL**，但脱敏阶段证据一致：Linux原Go短Key TLS+Rust M4客户端与服务器READY、正常Rust owner保留；另一**真正Python标准库TLS1.3访客**通过同一raw443经Decoy TLS源站8443 ping/pong成功，源站侧也确认成功。首异常是在**后续缓存测试夹具由普通runner用户读取Go root进程写出的0600缓存**时遭到权限拒绝（Python pathlib.read_text），安全权限本身正确，不应改成可被runner读取。只在受限Linux测试脚本把缓存stat/JSON内容+mtime检查改为`sudo -n python3`，不记录明文或派生key；workflow退出时由root删除private cache。新SOURCE两次重新启动和Stop未通过前绝不宣称端到端PASS。
