# PLAN028 H1372–H1374 并行原始业务：x86 双账号三设备与 ARM64 两次真实物理重认证

**日期：2026-11-08。** 真实业务成功即限定范围 PASS；外部测试窗口设置不当引发的原始 CI FAIL 保留并独立追责，不把报告器红灯混为 Go TLS/Rust 真实产品失败。

## H1372 | x86 真实两账号三安装实例共享 TLS443

- [原始 Action 42454413647](https://github.com/lly8666/wbd-next/actions/runs/42454413647) SUCCESS。冻结原 Go TLS/Rust 二进制 `6c5fd909b9f42d1af89c698cdaabc79bbb72e589`。真四次 protected TLS 认证、2账户/3独立安装与/32租约、共享一个443和 Rust TUN，**70** 实际内核 UDP echo、同安装新旧代及另一个账号独立生存、原 Rust Stop/路由成功。
- 真实原 Windows 无参与：Linux x86 三客户端用户 outer `[1460,1460,1280]`，原 SYN MSS `[1420,1420,1240]`，内核 TUN OS MTU `[1389,1389,1209]`，服务器共享真实 MTU 1389 不因第三个小 MTU 误降。原7文件 ZIP SHA256 `7b2d8b6c1c32d9f038046939780eecbb6ab6d15f59b89a75b22f2a79c543ee6d` CRC 全 PASS。
- 证据：docs/evidence/M0/PLAN028-H1372-SOURCE6C5-X86-THREE-NATIVE-ACCOUNTS-INDEPENDENT-OUTER-MTU-PASS-20261108.json

## H1373 原CI红灯（仅 fixture 时间窗）与 H1374 同原二进制 PASS

- [H1373 原始 Action 42454413776](https://github.com/lly8666/wbd-next/actions/runs/42454413776) 编译真正 ARM64 原 Go/Rust 产品成功，三个原 TLS 认证端均上线，Normal 两次原物理改动触发新原代和 Old Stop；但是旁边 Game4 真实 UDP 只采样 `32×0.4s=12.8s`，未覆盖第一轮真实重认证到 Ready 的约 **19.064s**，导致 `t1[0] < change < ready < t1[-1]` 纯场景时间窗口断言失败。原始 Action 保留 FAIL，不按本次短取样直接给完整业务 PASS。原8文件 ZIP CRC全PASS SHA `94a48443e987e45aba1cb95dd7a8fce4befaa002d7b0d59a3c97a600aba288c7`。
- [H1374 原始 Action 42454761994](https://github.com/lly8666/wbd-next/actions/runs/42454761994) SUCCESS：只扩展原 Game4 两个观测窗为 `64×0.4s=25.6s`。ARM64 Normal 原始 authenticated generations **1→2→3**，原 Old Stop **1、2**；源 IPv4 **10.25.0.4→10.25.0.9→10.25.0.4**、真实 NIC MTU **1500→1280→1500**，Normal 原 Rust TUN 真实 OS MTU **1389→1209→1209**，Game4 真实 TUN MTU **1358**、owner 代保持。
- Game4 真实内核 UDP 两个完整源切换时窗各 **64**，Normal 两次新代 UDP 各 **16**，原三客户端初始 UDP `[12,18,18]`，真实 OS 命令到新完整授权就绪 **17,535.88ms / 14,235.64ms**（不是静态网络 gap），各账号停止与服务器共享 TUN Stop 最终全通过。
- **关键：H1373 与 H1374 实际 Go 客户端、Go 服务器、Rust so 三个原始二进制 SHA256 全部完全一致**：client `e5bb2b…`, server `14236b…`, Rust `04d7f3…`。只是场景覆盖窗口修复；原产品业务未替换。原 H1374 10文件 ZIP CRC全PASS SHA `6c0c0f044879c4330e6c2c5f8e68a11de0fe0fa8b98b1cf451d52a284a450707`。
- 证据：docs/evidence/M0/PLAN028-H1373-H1374-SOURCE26A4-ARM64-NORMALOFF-TWO-PHYSICAL-REAUTH-GAME4-SIBLING-PASS-20261108.json

## 剩余硬验收

Windows 双张**签名 Wintun 原生内核 UDP**先前 H1369 已验收，但这不等于两台同时运行的**原 Go TLS/Rust 双账号 Windows 产品客户端**。当前 Windows native Normal `AutoLease:false` 并要求预先配置 /32，而 server 单 `--manual-client-lease4` 不能为两个独立账号各颁不同/32；应先安全贯通认证后按账号绑定不同手动/32或 Windows 全生命周期 AutoLease，随后真实 Windows/WSL2 A→A+B→B。同时旧 H998 same-socket hot MTU FAIL 和最终两条1800s L3仍开放，PLAN028 **IN_PROGRESS**。

```feature-impact
{"kind":"none","ids":[],"reason":"H1372-H1374 test-only parallel workflow and time-window witness correction, plus original business evidence; no production Go/Rust code or catalog cards altered, Windows 2 authenticated-product scope still NOT_RUN."}
```
