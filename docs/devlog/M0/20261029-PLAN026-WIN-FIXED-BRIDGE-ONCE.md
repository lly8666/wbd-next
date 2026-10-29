# M0 PLAN026 — Windows 源装配去重（实际编译首错）

2026-10-29，新来源 `06bc1287` 的 Windows Go 预检 `40818630086` 首错为 `competing original/overlay owner: r0/go_overlay/internal/realityfront/bridge_v4_windows_fixed_stream.go`。旧 WAL 直接读取 `manifest-plan020-m0.json`，而完整 Windows 预检在该 manifest 之后还逐个拷贝 `EXTRA_BRIDGES`，此前两个入口分别缺少/单独拥有这个固定流桥。现以**manifest 唯一装配入口**为准，删掉 `tools/prepare_windows_wiring.py` 中同名的第二次拷贝（同文件的测试桥仍保留）。无原Go产品逻辑变更，无改变 Rust FEC2/Auto 阈值或 M4 Stop。源 `d41` 的 Go/Rust便宜回归成功不代表此源码其他两端资格已通过，完整弱网序列仍未启动。

```feature-impact
{"kind":"none","ids":[],"reason":"仅将现有Original-Go Windows FixedStream单份拷贝集中到唯一manifest，避免旧WAL缺文件和新预检重复安装，不改变产品行为。"}
```
