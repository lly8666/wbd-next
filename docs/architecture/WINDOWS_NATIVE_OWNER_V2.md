# Windows NativeOwner 方案B：共享 Rust 协议、两个固定 I/O worker

**状态：设计，未实现。** 2026-10-28 PLAN026 优先于旧模块页对 Windows“Go热路径可保留”的描述；Linux既有可用原Rust raw/TUN不因本包修改。详见 [完整任务/复用表/验收](../decisions/M0-PLAN026-WINDOWS-RUST-NATIVE-IO-OWNER-20261028.md)。

```text
     Windows Go (FakeTCP/uTLS/credentials/WFP/DNS/routes/WAL/GUI)
             | low-rate: verified admission + native device lease
             v
           Rust WindowsTunnelOwner (long-lived tunnel epoch)
           |                                     |
      TX worker (1)                          RX worker (1)
      Wintun RX ring/event                   pcap_getevent per exact-flow RX handle
      AEAD/PN/M2/FEC/Game                    M3 authentication/PN replay
      shared Npcap TX handle                 Wintun allocate/send ring
      bounded ready batches                  bounded out-of-band feedback
```

## 资源不变量

| 资源 | Go | Rust |
|---|---|---|
| Wintun adapter/session | 唯一创建/OS身份验证/最终EndSession | 仅借用同一session进行所有业务读写；停止后归还 |
| Npcap每lane RX `pcap_t` | 初始化握手、停Reader、移交精确frame/handle | 单RX worker独占capture；新lane动态注册 |
| Npcap shared TX handle | 不碰稳态发送 | 单TX worker使用专用同NIC pcap_t；real copied-prefix disposition |
| OS WFP/DNS/routes/MTU/WAL | 全生命周期唯一控制 | 不写系统配置；只读已绑定有效状态 |
| AEAD/PN/M2/Health/Game | 不做稳态业务 | 同一个 ProtectedScopedOwner和shared Game adapter，按lane分别建key/seq |
| Tunnel epoch | Go OS owner持有 | Rust校验；换lane不变 |
| Lane incarnation | 每次真实TLS得到新一代 | Rust原子替换active，旧代 bounded draining |

稳态两个Rust worker总数固定，不是每lane两线程；每lane只增原 Go handshake时已打开的精确BPF capture handle及有界state。Npcap读取指针仅在本次pcap_next_ex有效，ring读到的包立即释放/复制到原生Arena；不把Go heap指针直接传Rust或保留跨回调。Npcap TX/RX不同句柄，避免同pcap_t跨线程无锁并发；DLL生存期必须覆盖Rust handle Stop/close，恰好一次close。

## 事件/性能/Stop

仅在Win32 native pcap/Wintun events、owner update/stop与 Rust M2/Health 真正到期唤醒；`pcap_getevent`能力在物理/Runner核实，不可靠就写事实支持替代，不回退到Go每5ms轮询。批次仅取已ready、不等凑满；固定密文和driver三态Accepted/Uncertain/NotAttempted不因语言边界修改。正常 I/O 不抢全局 registry mutex、不每包解析DLL proc、不每包查 PnP、不 per-packet log/heap Vec clone。真正效益需比较CPU秒/GB、每百万包、P99首次交付、空闲唤醒、Go CPU、Rust/内核CPU、进程RSS和Npcap driver丢包delta。

`RequestStop`停止新loan并唤醒线程→Rust RX/TX join→归还 ring/pcap/arena及延迟控制→`QUIESCED` completion→Go EndSession、WAL/WFP/DNS/route cleanup。清理失败保留owned恢复，不假报断开成功。动态lane用 `Prepare/Commit/Abort/Retire`，旧lane与新lane的PN/seq、四元组、capture分离；旧lane结束前保持Wintun和OS不变。

## 与旧文档的关系

`docs/architecture/HOT_PATH.md`、`modules/10-LIFECYCLE-QUALITY.md` 中旧“Go可以维持direct-hot-path、Auto/Health保持Go”等是阶段性历史选型；PLAN026生产目标要求 **Windows V4业务包不经过 Go**，例外必须明确列为 UNWIRED/non-native，不能宣称Go待机。Rust控制器只能有一个；短期Go低频Auto冷策略可继续用直到Rust替换有实证，不能重复Auto actor。
