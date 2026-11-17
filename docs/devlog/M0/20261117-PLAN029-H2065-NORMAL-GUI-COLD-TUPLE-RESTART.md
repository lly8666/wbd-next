# PLAN029 H2065｜普通 GUI 冷重连 FakeTCP 四元组复用首个失败

- **最新真实第三轮**：产品原编译 SOURCE `0e57cab2d53e2c95962eb673050fa54695fd3665`，fixture `b06e982341bf81df14523e900f3b8379a2d5e856`。三个 Windows2025/WSL2 独立 VM 均已启动原 Linux Rust/Go 与 Windows GUI/Go/Rust；重用 hash/driver/真实首次 Connected、1460/1389、owned Stop PASS，**第二次 GUI 用户按钮本身已真的启用并点击**，不是旧 WSL2/GUI 夹具故障。
- [GUI Action 44015496947](https://github.com/lly8666/wbd-next/actions/runs/44015496947) artifact14298916464：首次 TLS/OS/WAL/Stop 均 PASS，第二代原 Go 再发送真实 SYN 源端口41031，但没有 SYNACK，`original V4 TCP bootstrap failed: faketcp: client handshake failed`，第二代业务 NOT_RUN。
- [域名 Action 44015501963](https://github.com/lly8666/wbd-next/actions/runs/44015501963) artifact14299480286：两次真实独立物理 DNS UDP TC→同endpoint TCP53、服务器域名选择成功；第二代重新回到相同41031 TCP 四元组被拒，OS Ready、Direct/Tunnel业务 NOT_RUN。
- [TTL Action 44015506886](https://github.com/lly8666/wbd-next/actions/runs/44015506886) artifact14298508264：首次及 TTL2 过期后的 Windows 原生 DNS QNAME 均得安全 FakeIP `198.18.0.1`，真实 Linux 物理端收到两笔独立查询且应用上游DNS txid分离。第三次正常重连遇到同一 FakeTCP41031 无 SYNACK，第三阶段 NOT_RUN。
- **因果边界**：原 Go `m0WindowsOriginalColdClientPort` 已为同一进程 generation>1 轮换源端口；WinForms 普通 Stop 完整退出 Go，下一次新子进程 generation 重新=1，导致相同源IP+41031→服务器443。服务端原 raw FakeTCP 可短时保留先前已认证 tuple，不能要求正常重连先等过期，也不能把 Start 失败假装产品联网。
- **定向修复**：仅客户端 Go 冷控制每一次真实 TLS generation，在 portable OS WAL 目录持久化一个非secret bounded port ordinal，启动前原子替换+文件fsync，跳过失败代际而不是复用旧 tuple；同进程/跨进程均轮换，新增纯 Windows Go 端到端状态测试。完全不碰服务端/TLS wire/Go 热数据 path/原 Rust FEC Game/旧 WFP；保留 Stop 只清确定 live OS 资源，非secret持久状态用于下一次 Connect。
- 新代码会创建新的 SOURCE，**不能重用旧 EXE**；本次在原一条 native workflow 先构建一次新当前SOURCE产品并上传二进制，主 Action 验 H2061，上传后另两个独立 Actions 在各自 VM 复用同一新产品 SHA，保留真实三场分离。源码冻结前结果为 `IMPLEMENTED_NOT_TESTED`，不用单元测试冒充 Windows PASS。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback","windows-native-transport","client-domain-bootstrap","dns-split-ipv6"],"reason":"H2065 fixes real signed normal GUI second-generation same-FakeTCP-port first failure by cold persisted port ordinal; new SOURCE native still pending"}
```
