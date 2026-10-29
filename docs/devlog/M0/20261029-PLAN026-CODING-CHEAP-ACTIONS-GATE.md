# M0｜PLAN026 完整代码冻结前的 Actions 成本门

2026-10-29。调查 `main@122230fe` 的自动 `m0-wl-public-normal-full.yml`：普通 main push 会自动通过 Linux编译前置门进入昂贵真实签名设备/WSL2全模式执行。用户已要求先写齐整批产品/夹具，再Fixed→Game→Auto最后测试；这份调整为**施工期显式commit marker** `[plan026-coding]`，只让该类提交保留 cheap/ABI/Windows Go/Rust Linux库编译，跳过 Linux正式产品bundle与昂贵 native双OS。此前已经启动的 Actions 不取消、不改结果；冻结后必须用无 coding 标记的专门 source-locked workflow_dispatch 或 `[wiring-full]` 开始真实测试，并检查场景模式与source身份。

源链事实：`ae7afe` 是 Windows Fixed/Auto Rust-only candidate，无Game新native/Health；`122230`修正manifest及16KiB card, 其源构建单元成功但前期非产品；`58eb36`仅补模式化V2及Fixed/Game三个声明场景，尚未发出手动native测试。这份新增 gate 本身不是产品能力修复、不代表真实吞吐或Stop完成。

```feature-impact
{"kind":"none","ids":[],"reason":"只改变PLAN026代码施工期昂贵Actions的调度开关及测试守卫，所有用户功能、配置和已有精确SOURCE资格未变化。"}
```
