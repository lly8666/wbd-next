# PLAN029 H2066｜服务端第一次接管后，真实新 41032 SYN 被单会话逻辑主动忽略

原始 [H2065 域名重连 Action 44018142299](https://github.com/lly8666/wbd-next/actions/runs/44018142299) artifact `14299493168`，产品SOURCE `fb24fe784d960e3e8bf4ca63cc2a22332247e1dd`：客户端已修复正常 WinForms 新进程持久冷源端口，第一代真实 `41031 → 443` 与第二代 `41032 → 443`。WSL2 eth0 抓到第二代 **6 SYN**；没有对应的服务端 SYN-ACK。服务端真实日志只见初代 SYN、SYNACK、已认证 M4、最后 Stop；PID并未在第一次接管时退出。H2065 TTL 场首个/2s TTL后两次 `www.cn.example` 真实 FakeIP `198.18.0.1`，但重启仍在第二次 TLS SYN 阶段失败，第三次 NOT_RUN。

源码定位：`r0/go_overlay/internal/v4productcli/linux.go::runServer` 单会话分支在 `handoffCommitted.Load()==true` 后无条件跳过 **所有后来的** `IsInitialSYN`，即使 4 元组是新 `41032`。这不是掉线后 listener `Close()`，也不是假定 BPF 过滤新端口：`raw_detached_data_linux.go` 的过滤和对应 cBPF VM 单测已保留不同源端口及 SYN/ACK/FIN。**但单元不代替实网。**

原主线已有与此严格区分的 `runSharedMultiServer`，仅在服务端明确 `--manual-client-lease4` 或 `--lease-pool` 时使用：原 TUN/443 不变，新增每个真实 SYN 独立 FakeTCP Association、认证后 Rust M4 owner；同一已认证 manual /32 的新一代上来时在 B Ready 后才 retire A，最终一份 SharedTun Stop。对这次测试的真实手工客户端固定 lease `10.66.0.2/32`，服务端明确设置相同**受保护服务端分配**，不是信任客户端请求；不放宽未知端口或旧的 4 元组 BPF。

此次仅改 **测试服务器真实 CLI 配置**，把三条普通 GUI reconnect（含 domain/TTL）切到现有支持的单监听 shared manual /32 模式，并强制检查服务端两次真实 SYNACK、两次 M4 Session Ready、旧/新 Rust Stop 和最终 shared TUN Stop。复用 H2065 `44017075750` 的已编译 Windows EXE/Rust DLL、Linux Go/Rust SO SOURCE 与逐文件 SHA，不混成新产品版本；测试 fixture SOURCE 为本次提交 SHA。协调 push 不派第四条 native。不能把 H2065 失败改 PASS，默认单会话服务器仍只有单代能力，必须明确该配置边界。

当前 H2066 三条原生验收：`NOT_RUN`，后续须原 ZIP/report/Stop 才能说 PASS。

```feature-impact
{"kind":"updated","ids":["windows-native-transport","gui-config-feedback","dns-split-ipv6","client-domain-bootstrap"],"reason":"H2066 direct source+kernel witness of server singleton SYN gate, use existing verified shared manual-/32 mode to validate ordinary GUI two physical generations; new result pending"}
```
