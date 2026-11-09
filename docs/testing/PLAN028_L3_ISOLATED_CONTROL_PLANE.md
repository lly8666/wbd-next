# PLAN028｜L3 Windows/独立 Linux 控制面与数据面隔离（H1450）

**决定：暂停现有 GitHub-hosted `windows-2025` 上的 PLAN028 Windows+Linux 1800 秒 L3 资格场景。**保留真实短测和 ARM64 的 SOURCE 级资格，不把停测当成 PASS 或产品 FAIL。这个决定只限制同机 Runner/被测 VPN 的 1800 秒验收，不停其他独立有效任务。

## 1. 为什么此前的局部修补方向不成立

历史 Windows L3 原生 Action 42508261361、42517812264、42532903160、42540960361 均在不同业务时刻最后输出后，job 整体失败但 native step19 始终 `in_progress`，原生日志 `404 BlobNotFound`，上传和最终 Stop 未执行。新 SOURCE724a Action42546907707 的用户日志显示真实 Windows/Linux app 在720.2s 分别收到6698/6771，未见当时的 no-RX 断言；同段真实管理路由刷新 `added=0 repaired=0`，保留四条精确 owned/32，实际 Runner.Worker/Listener 当前公网对端2条。**这不证明 /32 一定没有隐患，却不支持在本场再补 /32 是触发修复。**`WL_NATIVE_L3_TEST_OUTPUT_IDLE_OWNER_ALIVE` 是60s正常业务打印间出现20/40s静默的*预期现象*，不等于故障发生。

分层判断：现有证据证实 Runner/CI 回报链的原始最终结果不合格；在最后一条业务输出后的产品生死、Windows整个OS是否挂起、具体公网出口/route table是否改变，原日志没有可追认的系统时序，均为 **UNKNOWN**。H1446已修复的 Python `subprocess.run(capture_output=True,timeout)` 被继承PIPE无限等EOF缺陷有确定性的离线回归，但 SOURCE724a 仍然在相同拓扑上暴露同类风险，不能据此宣布为本次的唯一根因。

外部交叉证据：GitHub actions/runner issue #4632，2026-08-13，描述 **无VPN路由变化** 的 Windows hosted Runner 异常失联、45分钟左右后被服务端清理、`BlobNotFound`、VM诊断无法回收。这只证明平台层存在相同表象的独立故障类型，**不是**这几场的直接根因证据。https://github.com/actions/runner/issues/4632

## 2. 更大的设计缺口：验收控制与被测网栈同故障域

现流程 `native-public-two-os` 在 GitHub hosted `windows-2025` 运行。该主机既承载 Runner.Worker/Listener、Actions stdout/工作目录/上传，又安装真实 Wintun、Npcap、Windows WAL/路由/防火墙，同时把 Linux 对端放在 Windows 宿主自己的 WSL2+netns。只钉住一开始识别到的 Runner TCP 对端/32，不能证明 GitHub 日志、动态 service endpoints、DNS、上传或 OS 自身依赖完全隔离。**同机独立线程心跳、看门狗、文件、60s业务打印，也都依赖同一个 Windows 宿主和 GitHub 回传链；断线时一起消失。**

另外，原先只比较 `0.0.0.0/0` 默认路由是否恢复，**并不足以证明实际互联网出口**：更具体的IPv4子网路由、Windows策略路由、接口 metric 和 GitHub 真实服务端目标的有效选路都可能不同。今后只允许基于独立实际进程/目标 IP 的OS选路证据来判断是否捕获 GitHub 流量；不能由DNS成功/默认路由不变反推控制面正常。

## 3. 唯一可接受的新 L3 拓扑

- **A：独立控制/取证宿主**（Linux runner或其他独立机器）。只管理/收集，不能运行 VPN Wintun，也不依赖Windows DUT单一 stdout/artifact；保持与被测 Windows 宿主不同失效域的时间轴、心跳、异常截断和来源签名/有效SOURCE。
- **B：独立 Windows DUT 虚拟机/设备**（不是承载 GitHub Runner.Worker 的那台机器）。运行固定SOURCE的签名 Npcap/Wintun+原始Go/Rust，拥有真实 OS route/WFP/WAL/MTU 和原始 Stop；其管理面与被测 VPN 路径物理/虚拟隔离且允许在 DUT 失联时由 A 强制停止/快照。
- **C：独立 Linux 客户端及共享服务器**，与 B 不共用 Windows 宿主/WSL2 失效域，真实 TUN/netns/认证 TLS443/同服两设备场景，不允许用 WSL2 故障域内的Linux进程假装C是外部机器。

架构前置门：独立A应当在故障发生时，至少持续保存 A 自身心跳、B 管理链路收到与否、C 独立发送与接收、B 产品应用事件（能收到时）、以及 B 被测前后的有效公网路由/接口/OS/WAL。无法获得这些时结论只能是 `ENVIRONMENT_BLOCKED/NOT_QUALIFIED`，不是数据面FAIL或PASS。

## 4. 新一轮采用先鉴别后长测

先做小型针对性**因果对照**：不改变 B 的 VPN 路由时 A/B/C 各自外部心跳稳定性；随后短时启动真正签名的 B Wintun（原始凭据与Linux独立客户端），A/C 必须在 B 日志突然中断后仍保留证据，比较 Windows 真实服务 IP有效选路、B 有无发送、C 继续收到与否、A远程管理可达与否。这个阶段不预设必需持续1800秒，不随意改MTU或扩展数据面。明确某环节首个失效才选一条修复，不反复用 GitHub Windows runner 刷种子。

短因果对照确认架构隔离并能完整捕获 Stop/恢复证据后，才运行**一场** Windows B+Linux C 真正1800s，并保留原有每5s双端UDP、每60s TCP、资源/RSS、单向最大无接收 <1500ms、Linux兄弟在 Windows A Stop 后仍存活、exact WAL/route/DNS/owned清理等全部硬门。若B整个OS丢失，A仍须报告 `ENVIRONMENT_BLOCKED` 与独立C业务计数，绝不伪造业务 Stop。

## 5. 实施阻塞与退出原则

当前连接的 GitHub-hosted Windows Runner **不具备可证明的隔离条件**；没有可用的独立 Windows DUT/远程管理地址和Linux物理/独立虚机资源证据，不能从此聊天擅自创建/声称该设备存在。因此 legacy `[plan028-win-linux-1800]` 在原 `native-public-two-os` hosted job 显式 SKIP。隔离平台/授权到位之前只允许不改变 Windows 主机网络的离线验收与已通过短测；PLAN028保持 `IN_PROGRESS`，Windows L3 `NOT_QUALIFIED`。

保留 H998 同socket热MTU旧FAIL；Android/用户物理设备 NOT_RUN；ARM64 eef2 两个独立1800s PASS_SCOPED 和 Windows+独立Linux e6aa 短测 PASS_SCOPED 均按原SOURCE复用。PLAN029/030不启动。
