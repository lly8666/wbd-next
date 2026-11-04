# PLAN028 H1081 — Windows WSL2 真 TCP 握手审计源锁修复

按最新 main/source `7b38d2baddaa41ab5e410d2533a1e8c396510745` 收在途 Action，不重新派发旧矩阵。H1080 [Action 41757222750](https://github.com/lly8666/wbd-next/actions/runs/41757222750) 的 Windows Go/Rust、Linux Go/Rust 构建都成功；唯一原生 Windows Npcap→WSL2 Normal 场景的 `tcpdump` 子进程在 Windows 发 SYN 之前退出。下载原 Action 13288579971 工件显示当前没有可检查的抓包stderr，也没有原始PCAP（按契约不上传），所以结果只能是 **FAIL_PRE_SYN_CAPTURE**，不能谎报已经验了ClientHello。

源代码核查发现 Windows Python 用 `Path.write_text` 生成供 WSL /bin/sh 执行的脚本。Windows 默认CRLF会让 shell 的 `set -eu` 出错；原 WSL 服务端生成脚本已用 `write_bytes` 而无此风险。H1081 仅将新捕获脚本改为明确 LF-only 字节写入、保留 `$$` PID 真实展开，并将捕获进程提前退出的真实 stderr + 返回码追加到已有Action日志，使下一次能严格抓到第一错误；在新Action前CRLF仍只是代码证据支持的疑似原因。

另一条独立 Linux/x86 原生日志来自 [Action 41756961106](https://github.com/lly8666/wbd-next/actions/runs/41756961106)：内层真实 UDP 及两端TCP已发生，但 TLS 字节审计器最后读 `server_ip` 未定义报 NameError。且 Windows 调用方传 `audit(raw,server_ip=peer)`，旧函数签名并不支持该参数。改为基于TCP客户端源IPv4+源端口、目标443及服务器反向四元组绑定单条原始流；可选参数仅允许OS读回的真实WSL2服务器IPv4，取消旧 Linux netns `10.25.0.1` 硬编码。保留原双向按TCP序号重组、ClientHello/ServerHello、TLS record长度、32B SessionID以及禁止WB-R1判定。新增 Python 小单测仅使用明确标识的**合成解析器数据**防止错误重现，绝不能作为线上TLS证据。

为高效测试，只在 `[plan028-win-tls-wire] [plan028-win-tls-reuse]` 标记下复用 H1080 已构建的确切SOURCE `7b38...` Windows产品 EXE/Rust DLL、Linux原Go服务端/Rust SO，先核 Git 源码差异/每个 SHA256，再执行**一Action一Normal原生Windows Npcap+WSL2场景**。不会再次编译产品或发起七模式矩阵；附 `[frozen-fixture-only]` 跳过因共享解析器变更而触发的 Linux二次构建。下一次真 Action 之前，Windows 首飞仍 NOT_QUALIFIED。

标准TLS契约仍要求后续完整 Finished/证书握手与同SNI/证书/MTU标准客户端基线的结构比较，不能凭首段解析或TLS成功宣称任意DPI不可识别。Windows物理网卡变更、健康Game lane重叠、CPU/p99、H998在线缩窄FAIL、旧ARM64 Game4FEC FAIL、远端ICMP未测按原证据保留。Windows+WSL2不计用户的Linux双端x86/ARM轮换。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1081 true WSL2 tcpdump source-frozen LF shell/stderr repair and exact dynamic TCP four-tuple audit, no original Go/Rust change; Windows TLS wire not qualified until real Action."}
```
