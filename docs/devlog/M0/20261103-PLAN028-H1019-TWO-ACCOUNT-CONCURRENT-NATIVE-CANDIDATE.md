# H1019｜PLAN028原Go真正并发多账号单端口＋共享Rust TUN，三真实netns准入候选

## 本次基于已通过的独立真实来源

`H1017` SOURCE `9c39b5878087bb201b4b318532ce9784684ab63a` Action `41583636961` native job `125743937176` **SUCCESS**：1个受保护TLS自动设备 `10.66.0.138/32` 用真正Linux OS装/读回，**一个Rust共享TUN内核reader**路由5包、unrouted0、backpressure0、reader_joined1，原Native M1/UDP/Stop 5包PASS；独立generation A→B替换时旧Stop不会误删新会话的Rust单测PASS。同二进制Game2/4单端口、Normal/FEC短smoke、1%真实512 offered/507 unique/5 missing都有限域PASS。来源写入`docs/evidence/M0/PLAN028-H1018-SOURCE9C39-SHARED-TUN-REAL-KERNEL-20261103.json`，不得冒称2设备原生已PASS。

## H1019新代码（本SOURCE前先完整两端实现后仅跑一次）

- `r0/go_overlay/internal/v4productcli/linux.go`真正启用自动租约服务端的**一端口、多真实original-Go TLS设备**manager：一个原本的`RawIPv4Endpoint`和`ServerAssociationTable(32)`，32条认证FakeTCP关联，每个原来的`V4LinuxServerProduct`拥有独立账户认证、immutable 16-byte TunnelID、epoch/incarnation、Rust M1/M3/M4 RAW/TUN内核handle及per-session Health。没有Go每包热路径plaintext/加密泵。完全复用原Rust `V4LinuxSharedTun`单reader，依据原Go认证租约路由给不同Rust发送owner。冷态认证失败只清理那条会话，不退出其他用户。OS全局TUN MTU不会由任何一个客户端的回包变更。
- 真正同一/32新generation只有在新原Go TLS/Rust worker开始并内核BPF成功排除已接管DATA后淘汰旧epoch；同账号另一安装ID与另一个账户的不同/32独立。拒绝没有保护TLS自动租约的路由绑定。
- `r0/go_overlay/internal/faketcp/raw_detached_data_linux.go`将已有**原cBPF五元组DATA排除表**从Game的2/4扩至最多32精确认证tuple，同NAT IP/不同TCP source port可共存；未认证新SYN与ACK/FIN/RST仍允许原Go控制接收，无Rust已接管DATA落回Go。无备用传输/record格式。对应原Go classic-BPF VM新增32并发tuple/同NAT新客户端/越界拒绝测试。
- `tools/m0-plan028-two-client-real-linux-netns.sh`实际三隔离Linux netns、一台bridge underlay server单443端口、两台独立Go client不同IP、Alice/Bob受保护用户名密码、各自随机安装ID派生 `/32` 租约。真实TUN UDP echo按 A先5，A+B**同时**各12，A原Rust STOP后B再5验收。服务端进程不得重启；同一真实Rust shared reader输出路由≥34及reader_joined、Rust两个原生Stop；所有应用皆真实Linux内核发出，不是Go包注入替身。
- `.github/workflows/m0-plan012-combined-functional.yml`继续使用同源码**一次编译**的原Go client/server和Rust .so，加入精确BPF Go单测和新三netns应用/Stop步骤；若新模式FAIL仍继续原有1%真实丢包/FEC/Game有限域工作以留全源状态，最后mandatory gate强制FAIL而不是继续验收。

## 不可偷换的边界

**H1019当前是源码候选/IMPLEMENTED_NOT_TESTED**，不承诺业务通过。原H1017只有一个设备；H1019本轮需从Actions看真实3-netns、同一port443、共享reader A→A+B→B证据。新并发接入首先支持自动租约Normal/off（原固定/Auto单设备继续有效），用户所需7模式（Game lane一端口跨设备组）、同账号多安装ID再加另账号同时在场、手动IP所有权、Windows/Linux真实网络通知与MTU改变、200/500ms风暴合并以及CPU原因证明仍需要后续本028工作；H998物理1500→1280在线缩窄FAIL/ARM64 Game4FEC FAIL，Windows/WLS2 Game4 bootstrap lane2 Action41579974280 FAIL均不改写。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Real one-port multi-account original Go protected TLS admission and 32-peer kernel cBPF exclusion now route to existing Rust shared TUN reader and per-device M1/M4 owners; exact three-netns A->A+B->B source-locked native gate introduced, no PASS before Actions."}
```
