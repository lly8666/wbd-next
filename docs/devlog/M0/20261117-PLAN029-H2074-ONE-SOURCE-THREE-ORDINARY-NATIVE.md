# PLAN029 H2074｜冻结新 SOURCE，一次编译三条日常原生场

接续主线 `fb84d98f67be05ec57161549d5b1de5bb1248d85`，H2072 Windows 正式 `start_native` 的 **实际 Entry** Health arm 已被新源码 native-functional/Windows Rust/Go 编译、ABI/跨ABI与纯组件 CI 覆盖；这些只等于 BUILD/UNIT PASS，不是第二次联网通过。H2073 governance Action 44031795000 PASS。上一真实 Action44025145100 依旧 FAIL，B RAW/tuple/TUN有包但未证实规范 Health，B OS Applied/Direct/Tunnel业务NOT_RUN。

本次采用原 `.github/workflows/m0-wl-public-normal-full.yml` 中已有的 H2065 **一次新SOURCE Windows EXE/Rust DLL、Linux Go/Rust SO 构建后复用**逻辑，不改实际测试场、入口或协议；commit marker 单次触发 1 条当前原 WinForms GUI Disconnect→Connect 及 **仅两条**独立 workflow_dispatch (`domain_reconnect`, `dns_ttl_restart`)，按各 SHA/manifest核对。当前为请求记录，全部场景 **PENDING/NOT_RUN**，不能在 runner 回执前写 PASS。仅此一轮有新假设的真实产品验证，不再重复旧 H2070 RAW/BPF/Defender 探针。

只取必要第一失败：Linux server B 后真实 M3 AEAD/unique PN kind1/Health hint、旧 A /32 更新和精确 Stop、Windows B OS 1460/inner1389 Applied、单 DNS 两出口 TCP/UDP、第三次 TTL FakeIP 与正常重新连接。已实现的 P1/P2 纯组件、旧 Game4/FEC/Normal外观等历史证据保留，不跑极端 CPU/RSS/IPv6 全矩阵。新增控制只影响 native Normal/Fixed/Auto 冷启动 Health；实网通过后对原模式做小范围接线/编译回归，不能拿单个子测试替代产品结论。

如当前新源码 Action 仍不通过，按首个新增失败修复并记录 FAIL，保留单条真实场景重测的权限；绝不放松服务端认证门或假 OS Ready。
