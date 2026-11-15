# PLAN029 H1911｜10GiB 原签名Win+Linux二进制一次编译，多次SOURCE锁定实网对照

- 复用[H1909 Action43700145002](https://github.com/lly8666/wbd-next/actions/runs/43700145002) 已签名**SUCCESS**的真实Windows2025原Go EXE + Rust release DLL（同run artifact`m0-wl-windows-product-binaries-64f6819460f7f950f13bc7d10659a6f4552b28b6`）及Linux原Go/Rust`m0-plan024-linux-product`，两者当时均验证相同`source_sha=64f6819460f7f950f13bc7d10659a6f4552b28b6`，30天保存且仍存在。H1909 10GiB真传输 SHA、TCP FIN、96B Tunnel UDP、owned Stop已通过，H1910单独归档CPU。
- 本SOURCE只改**GitHub工作流、离线测试与M0记录**，不动`crates/**`、`r0/go_overlay/**`、Cargo和ABI。新增精确独立标记`[plan029-v3-real-p2-reuse-10gib]`，指定run`43700145002` + SHA`64f6819460f7f950f13bc7d10659a6f4552b28b6`用于Windows/Linux artifact selector；严格`gh api run`同repo+同head+**conclusion success**，再次验证每一EXE/DLL和每一Linux二进制的manifest、byte SHA256、锁定官方ISA-L和Win V3原导出。现有`git diff --name-only original_sha current_sha -- crates r0/go_overlay Cargo.lock Cargo.toml tools/prepare_windows_wiring.py`必须**为空**，否则fail-closed，不借标记绕过原build。
- 编译任务本轮能跳过的原Windows Go编译、WinRust/Ubuntu Rust组件回归和Linux二进制编译全部跳过（**已在H1909 SOURCE跑完，文件未改**），同一GitHub runner仍执行cheap assembly、Python静态契约和真实签名Npcap/Wintun、WSL2 Linux物理内核路径。继承此前标记`[plan029-v3-real-p2-bulk] [plan029-v3-real-p2-500-700] [plan029-v3-real-p2-long-ab]`，强制一条VM原owner先物理再Direct分别跑2GiB单向+1.5GiB双方向与96B Tunnel UDP长覆盖、owned Stop。所有16KiB档位和SHA/FIN/CPU user+kernel单调验证保留。
- **本SOURCE NOT_RUN**：不能把前一VM CPU数复制为本VM结果；即使新Action再通过，两个VM的多次CPU/GiB才是跨runner复现，不是严格同VM“代码版本”因果。任何产物缺失/过期、Go/Rust实际不一致、签名网络业务首错、Stop失败保留真实红灯。不做重流量跨job并发，否则负载影响彼此的CPU/GiB。下一轮依据复测稳定性先定位Rust TX/WinSock扫描/内核NPF/Wintun路由层成本，不把物理socket误称“纯Tunnel比较”。

```feature-impact
{"kind":"none","ids":[],"reason":"H1911 only adds exact source-locked GitHub Actions product binary reuse, compile skip and test-only contract; no product feature or release code change."}
```
