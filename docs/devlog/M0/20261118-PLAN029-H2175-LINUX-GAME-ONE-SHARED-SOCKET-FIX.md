# PLAN029 H2175｜Linux Game2/4原服务端共享原生AF_PACKET冷就绪门修复

H2174 [Action44256427127](https://github.com/lly8666/wbd-next/actions/runs/44256427127) 的 x86_64/ARM64 **双原生Linux**各已在同SOURCE `03025191f46744bcbc90378440bd03973391cd3a` 下通过Normal、Normal Fixed、Normal Auto三场真正Go TLS认证、Rust M4、双网命名空间TUN和双向内核TCP/UDP echo，MTU1460/Normal DF、仅自有TUN禁IPv6和双端owned Stop/namespace清理 PASS_SCOPED。Game2则在**开始第一个SYN之前**因旧夹具等待`/proc/net/packet >= game_lanes`卡死；实际原Game server进程未退出、server.log已创建TUN但无Game TLS，因为client根本未启动。保留这两份首个失败、Game4 NOT_RUN。

调查当前正式原Go源 `r0/go_overlay/internal/v4productcli/game_linux.go` 的 `runGameServer`：明确写有 `One real AF_PACKET listener per server port, not one ... per Game lane`，且仅调用一次 `OpenRawIPv4EndpointWithOptions(ReceivePort:c.localPort)`，之后在同一个原socket上收Game2/4多条独立端口TLS认证会话。因此将现有`tools/arm64_linux_netns_smoke.sh`的Game预SYN要求从`AF_PACKET >= n lanes`改为 **Dedicated server netns中的真实AF_PACKET >=1**、继续阻止0 socket时发SYN，不允许没有真实kernel FD时绕开守卫。真正每lane TLS认证、Rust M4 kernel copy、Game4 FEC原parity、实际双向IP业务、Stop的旧严格守卫均保持，不靠计数宣称Game正常。

`tests/test_m0_plan029_linux_dual_native_scope.py`加当前Go one-receive-port源码与exact socket门检查，保留原冻结ARM64 fixture旧语义其他路径；新SOURCE原生两ISA 5短场实验按首错记录、不刷旧Windows20场、不改产品Game逻辑。Linux真的五场PASS需单独新Action/产物，编译/旧Normal不能代替。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct an overstrict test-only Game cold AF_PACKET readiness count from 2/4 per lane to one genuine original-Go shared-port listener, keeping all original auth/M4/FEC/kernel/Stop acceptance strict."}
```
