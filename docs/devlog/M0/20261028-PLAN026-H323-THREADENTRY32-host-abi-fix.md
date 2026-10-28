# PLAN026 H323｜Windows线程采样器 Linux CI 位宽首错（2026-10-28）

精确源码 `68816931b82b6152e97d6e5bb152a056882000f6` 的Normal-only Action40652451627在便宜Linux unit门首错：Python `ctypes.wintypes.DWORD` 在Linux下按host `c_ulong` 可能为8B，误将Win32 `THREADENTRY32` 7×4B测试为56B，预期真实Win32 ABI为28B；业务、Rust Windows编译/设备并未执行，不登记网络失败。

将 `THREADENTRY32` 与 `FILETIME` 的网络外测量结构显式写为 `ctypes.c_uint32/c_int32` 固定32位宽，避免把宿主平台宽度假定作Win32。运行中的Rust TX/RX没有额外锁、线程或包回调。本批重新启动现有单mode真实Actions，以新SOURCE记录。

```feature-impact
{"kind":"none","ids":[],"reason":"修正测试采样侧Win32 C结构在Linux测试宿主的32位布局，产品默认、wire、加密数据热路径和Go冷层无变化。"}
```
