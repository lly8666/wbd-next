# PLAN029 H2054｜GUI 真 WinForms 双出口 Stop 已入原日志，修正 STA Dispose 非零退出

- [H2050 原生Action43998891197](https://github.com/lly8666/wbd-next/actions/runs/43998891197) 完成**同源 WinForms 原保存/连接、原Go TLS/Rust owner OS Applied、outer1460/inner1389、原Windows/WSL2内核Tunnel UDP/TCP、CN Direct UDP+FakeIP TCP32KiB与FIN，并见原Stop WAL readback**。客户端日志精确含 `WBD_WINDOWS_OS_APPLIED`、`WBD_WINDOWS_CLIENT_READY`、`WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1 planned=1389 applied=1389 outer_config=1460`、`M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS`、`WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1`、`PLAN029_REAL_GUI_WINFORMS_BUTTON_STOP_WAL_ABSENT_PASS`；独立Linux还记录`V4_PUBLIC_NATIVE_STOP_DRAINED role=server`。
- 但整个Action原严格`w.returncode==0`失败：末尾`Unhandled Exception: System.InvalidOperationException: Value Dispose() cannot be called while doing CreateHandle().`，来自测试STA`finally form.Dispose()`与WinForms异步状态控件创建竞态，**不是Go/Rust网络回滚失败**。本源仅取消测试进程额外同步重复销毁；不跳过Go原生Stop、不放松OS Applied/业务/外部EXIT0断言，不以产出的GUI marker替代EXIT0。
- 本提交`[plan029-real-gui-cn]`仅发起单次真实同SOURCE验证；上个H2050保留FAIL，直到本SOURCE Action完成才可收口。H2051资源/TC单独在途，不重复H2031/H2041。<br>

```feature-impact
{"kind":"updated","ids":["gui-config-feedback"],"reason":"H2050 real signed GUI Connect/OS Applied/Go Rust business and WAL Stop observed but test Form.Dispose STA exception forced action FAIL; remove duplicate harness Dispose and rerun exact original GUI."}
```
