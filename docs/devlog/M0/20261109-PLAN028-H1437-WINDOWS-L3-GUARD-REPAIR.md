# PLAN028 H1437｜Windows 1800s 的原外层 Watchdog 在启动即退出

根据 H1436 双平台原始验收，ARM64 两独立 1800s 已 PASS_SCOPED；Win-Lin Action42508261361 第19步原生真实业务没有最终报告、Stop或成功收尾，原 job 日志返回 404 BlobNotFound，故仍 **NOT_QUALIFIED**。先多角度读现行工作流与 **真正运行的** `tools/m0_wl_windows_step_watchdog.py`：工作流只在明确 `[plan028-win-linux-1800]` 时传入 `$wholeLimit=2600`，Python watchdog 首行却仍 `assert 30<=seconds<=1500`，**无条件启动即失败**；PowerShell `Start-Process -PassThru` 能得到非空进程对象，原没有检查进程是否已经退出。结果失去了外层全步骤守护。这是**确定的夹具缺陷**；不是已证明 Windows 产品在30分钟内业务中断的因果结论，也绝不能据此把原 native FAIL 强行改 PASS。

H1437 唯一修正为标准各模式保留 `<=1500s` 看门狗限制，`WBD_PLAN028_WIN_LINUX_L3=1` 例外明确允许最多2600s；PowerShell 独立 PID 启动后350ms强制 Refresh/HasExited 检查。新增真实独立 Python watchdog 进程离线单测，带预置退出标记快速验证普通1020通过、普通2600必须拒绝、L3 2600允许、L3 2601拒绝，且判定守护进程活性。仍一个 Windows Wintun 和独立 Linux Bob，原 Go TLS443/Rust/ISA-L/record/FEC/MTU 全部不动。之后按用户同意的长测只做**一次修复后的 Windows L3**；若仍失败按原始业务证据判断，绝不代替产品 PASS。

原 Actions/证据：`docs/evidence/M0/PLAN028-H1436-ARM64-2X1800-PASS-WINDOWS-LINUX-L3-NOT-QUALIFIED-20261109.json`。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix broken L3-only independent Windows test watchdog upper-limit and check actual running guard; standard max remains unchanged, no product behavior modified."}
```
