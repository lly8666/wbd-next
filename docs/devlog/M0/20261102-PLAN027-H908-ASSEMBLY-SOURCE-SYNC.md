# PLAN027 H908｜同步 Windows 原始 Go 装配 SOURCE，修复预检失败

- H907 [Action41415356605](https://github.com/lly8666/wbd-next/actions/runs/41415356605) 在 **cheap preflight** 报 `assembly blob mismatch: r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go`; Windows Go/Rust 编译和真实双 OS 测量 **NOT_RUN**。不把装配失败误作 H907 产品恢复 FAIL。
- H908 仅更新 `r0/go_overlay/assembly/manifest-plan020-m0.json` 中两条已有 `kind=create` 的完整新 Git blob 结果：`m0_native_v4_windows.go` → `d4c7d840bab2b597bc7166559558a2e8e217fb88`；`m0_native_v4_reauth_windows_test.go` → `03e2f15fcea14d60e5cff76575775720deb6c580`。原始 Windows Go 文件、现有 Rust、原密文、TLS 和厂商驱动无额外变动，仍由原 `prepare_windows_wiring.py --check-only` 强制验证，没有绕开 SOURCE。
- H905 真实黑洞已证明 Windows 旧 Health-dead6 owner joined 和 `wal_kernel_crypto PASS`、Linux 同样成功退旧；在实际 105s IFB 恢复之前 Windows gen2 FakeTCP handshake 超时导致进程退出，管理 DNS/产物上传并未失败。H907 原始 Windows Go 补至多两次经过认证失活与成功 Stop 后、下一代尚未 Applied 的冷传输超时重试；H908 用这一变更后的 **exact SOURCE** 再验一次，当前产品结果 **NOT_RUN**。
- H903 SOURCE5cee 的老卡住 Actions 原样独立留存，不能当 H908 验证结果或重复派发。

```feature-impact
{"kind":"none","ids":[],"reason":"Update exact existing Windows Go assembly pins for existing authenticated-dead cold-retry code and test; no additional feature, setting, or protocol change."}
```
