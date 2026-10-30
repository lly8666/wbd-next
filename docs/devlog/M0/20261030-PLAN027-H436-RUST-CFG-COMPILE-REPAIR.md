# PLAN027 H436｜H434 Linux native G2真实编译报错

H434 SOURCE 9a634623 / G2 Action40980918637 的真实 Rust 错误：`v4_owner_crypto.rs:589` 为了允许 Linux/Windows 同一个 M3 seq64 预览，`#[cfg(any(target_os="windows",all(...)))]` 少一个闭合括号，令仅涉及该owner的多组Rust job FAIL；fake-platform在同SOURCE已PASS。只增该编译守卫括号，不修改构包、安全或配额行为，保留原G2失败和新SOURCE需要重验。当前其他source CI在途不重dispatch。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Fix one Rust cfg delimiter in dual-OS original-owner seq64 preview, surfaced by actual source-locked G2 compiler."}
```
