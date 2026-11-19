# PLAN029B H2116｜B4单测导致原Windows组装的精确Go测试blob pin不一致

H2115 SOURCE `11596bbb17e08a667f4f838080e7c2c09635e3f9` 的 [M0-WIN-LINUX Action44119996395](https://github.com/lly8666/wbd-next/actions/runs/44119996395) 首个 cheap job134168406022 **FAIL**，`python tools/prepare_windows_wiring.py --check-only` 报 `ValueError: assembly blob mismatch: r0/go_overlay/cmd/wbd-client/m0_plan029_cold_split_windows_test.go`。新B4三代原Go测试改变该测试文件 git blob SHA为`4097f533b7c88e8a2389edacae1a96e1e8a2fc56`，原`r0/go_overlay/assembly/manifest-plan020-m0.json`仍钉旧`0c51df873d1adc6d975f7c684934c6347f0218fc`；原 Go 产品还未执行。H2116**仅**换这一个 manifest create 操作的`result_blob`，其余138条以及 pinned 原Go/SOURCE不变，不通过放宽`--check-only`或文件hash来绕测试。Go Windows原冷构造/ Rust历史FakeIP纯测试仍要按SOURCE编译/执行，未得到Go CI绿灯前不把H2115转为PASS。

H2115 governance Action44119996108已经SUCCESS；独立Linux Rust组件成功，Windows Rust/WinForms/Go配置独立行动仍按其实际原回执，不互相推断。H2112独立真实签名B3 Win2025 Wintun /128 IPv6+IPv4/Stop依然`PASS_SCOPED`、全宿主IPv6不保证。B4实际WinForms三代+缓存/晚回调/Stop、Game2/4和B5同VM10Mbps CPU/GiB/p99均NOT_RUN；029/029B未关、030未开。

```feature-impact
{"kind":"none","ids":[],"reason":"H2116 only updates one pinned assembly result_blob for already-added Go cold-generation test; no production behavior or catalog record changes"}
```
