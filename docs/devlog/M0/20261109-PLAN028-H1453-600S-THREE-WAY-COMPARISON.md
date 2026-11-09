# PLAN028 H1453｜一次 SOURCE、三路平行：600s 真实 Windows+Linux、750s 干净 Windows、Ubuntu 异地主机

用户明确要求提高排障效率，不要为每个猜想先修一个补丁再盲跑1800s，并且授权用600s真实应用测试顺便寻找其他bug。本次继续冻结 VPN Go/Rust 产品、TLS/FEC/MTU/业务硬门，只改变PLAN028测试夹具和Actions接线。

**为什么短L1 PASS、长L3时常无回执？** 短测H1415只在初次两个独立认证客户端、内层UDP/TCP可用、A Stop B继续、原始owned清理后快速退出；L3进入长期观测：每5s双端UDP空洞、每10s Windows Runner management /32 CAS刷新、每60s双方TCP、每120s RSS与CPU采样，并让Windows GitHub Runner/真实Wintun和WSL2独立客户端共用的宿主活足1800s。既可能暴露产品的长时间缓存/重试/线程/句柄增长，也可能是更多系统调用和长时间主机网络操作诱发Runner/WSL2/日志控制链死锁/断线。这几类需同时测，不把旧Job FAILURE当产品FAIL。

**一场三臂对照，不是三场重复1800：**
1. **600s真实产品** `[plan028-win-linux-co-client] [plan028-win-linux-600]`：原来唯一signed Windows Npcap/Wintun客户端Alice + 真正独立身份的WSL2 Linux TUN客户端Bob，同一个Go标准TLS443/Rust M4服务端；保持每10ms真实业务、每5s收件<1500ms、整段双向实际UDP >=4167每端/echo>=97%、双方原始TCP交付>=9、原始两端资源采样>=4、management exact /32刷新>=20、原始Windows Stop后Linux业务继续、Linux/server Stop、WAL/路由/owner精确恢复均必须成功。专用结果 `PASS_SCOPED_REAL_600S_BOTH_CLIENTS`，绝不引用/显示原1800s通过。
2. **750s干净Runner对照**：另一台同型 `windows-2025`，**不调用Wintun、Npcap、WSL、任何网络改写**，每15s打印Worker心跳，独立产物。它验证GitHub托管Win OS/日志长时间稳定性的基线，非同一VM严格A/B；若它也失败，基础设施可能性升高；若它成功而产品组失败，优先分析被测主机特殊扰动/WSL等，但都不是自动的产品根因证明。
3. **Ubuntu跨宿主状态观察**：`ubuntu-24.04` 读取同一Action的native+clean Windows两个jobs状态/step（同SOURCE），每15s存独立产物。此观察不能看Windows网络栈或Linux真实收发，只能区别两Windows Runner是否向GitHub正确回报。不取消、不重派也不自动宣布产品PASS。

**定位性能/资源**：每120s新记录 Windows RSS/private/threads/handles/CPU + Linux server/client RSS/CPU；将真实采样打印到日志，同时写入终端JSON，使后续静默前仍有斜率。新增真正限时：600业务拥有独立940s Windows原生子进程上限，外层完整WSL步骤1280s watchdog，既不延长其他场景，也不改原1800s原有2250/2600预算。清理/恢复不因测试超时被判PASS。

**禁止扩大解释**：旧 SOURCE724a Action42546907707 原生阶段19 `in_progress` 直至 GitHub FAILURE且log Blob404，最后用户可见业务到720s健康。H1450阻止新1800 marker已验证；本次用**独立600 marker**经仅一次真实重跑寻找差异，不解除1800隔离阻塞。600s可得局部PASS或明确的业务FAIL／ENVIRONMENT_BLOCKED，但 L3 正式1800s仍须隔离A控制/B Windows DUT/C独立Linux宿主、原始Stop和独立Windows有效路由取证。ARM64 eef2 两次1800 PASS_SCOPED保持，H998 HOT MTU FAIL保持，Android和用户物理NOT_RUN保持。无PLAN029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"PLAN028 exact 600s short differential and control/observer jobs, Windows/Linux resource diagnostics; shipping product and protocol untouched."}
```
