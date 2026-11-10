# PLAN028 H1551｜Win1+Linux4 实际 600s 防 320s 原生 supervisor 提前杀进程

- 新用户目标 H1548 单签名 Windows Wintun Alice＋4个 Linux netns 真Go/Rust账户，共享Linux TLS443/五模式，200ms/方向 0/30%及内核外层双向250–300Mbps完整600s，严格真实M4、UDP/TCP、所有六个owned Stop。H1549 修复此前物理 Runner 管理路由精确收据授权，验收前原线本次已全部SOURCE、Linux/Windows Go/Rust编译 PASS。
- 继续审代码时发现：H1549的 `WBD_PLAN028_MIXED_SCENE` 只标记新场景，旧 `native_batch_deadline()` 仍从 `WBD_WL_PUBLIC_MODES='normal'` 得 **320 秒**，外层全WSL watchdog因RUNNER_MGMT_PIN只有 **780秒**。这必然让真正600秒五账户测试提前杀死，不是可以认成真实产品失败的结果。旧source b628 [Action42857999491](https://github.com/lly8666/wbd-next/actions/runs/42857999491) 在本次修改时已进原生Windows DLL构建；原始结果保留，**绝不把运行中当PASS**。
- H1551新增**精确混合场景**监督预算：只有 `scene=loss0|loss30`、Normal模式、单Windows GUI不绕过、物理Runner已自有route/32、原1460外层同时成立，真实唯一原生子树PID 940秒、父级HyperV/WSL watchdog 1180秒，严格小于整体 step24min；别的 Normal/旧105/旧L3/Game保持原数值。Windows原生数据Plane、WFP、Go TLS/Rust/租约、源IP/MTU、收据及原有CPU/内存容量保护均不变。
- 离线合同 `tests.test_m0_plan028_h1548_win1_linux4_scope` 正负覆盖完整600s的真场景和任一scope不对均退回320s；工作流仍为**单个** `native-public-two-os` job 两个独立Runner matrix，提交保留精准触发token `[plan028-h1548-win1-linux4-600]` 用本次真正可跑足600秒的包装Source新编Go/Rust，旧SOURCE运行不能覆盖它的成功或失败。
- 历史Linux x86 300–350Mbps 0%333.930/30%304.271已按用户接受记`PASS_SCOPED`，当前Win1+Linux4外层250–300**仍未验证**，PLAN028 `IN_PROGRESS`。

```feature-impact
{"kind":"none","reason":"CI-only exact mixed-Windows/Linux 600s original native PID budget and parent WSL watchdog boundary; no product code, wire protocol, runtime feature or foreign route safety change."}
```
