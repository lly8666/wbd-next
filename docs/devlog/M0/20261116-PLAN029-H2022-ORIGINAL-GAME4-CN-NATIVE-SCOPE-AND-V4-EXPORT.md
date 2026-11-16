# PLAN029 H2022｜Game4 CN唯一显式native selector及真正V4 DLL能力门

- H2019 [原Action43892285699](https://github.com/lly8666/wbd-next/actions/runs/43892285699)、H2020 [原Action43893005589](https://github.com/lly8666/wbd-next/actions/runs/43893005589) 完成Windows/Linux Rust/原Go单元和编译，但`wiring-contract.outputs.native_smoke=false`：`tools/m0_native_ci_scope.py`只认识旧Normal029标记，纯manifest/夹具提交即使带`[plan029-game4-cn-real]`也**跳过**原生网络。不能以编译绿当Game4真出口。
- H2022在原source scope explicit markers新增该一个Game4正名并补正/负测试；Windows原签名生产Rust DLL组合`m0_v4_probe`条件新增`WBD_PLAN029_GAME4_CN_SCENE`，拷贝DLL后检查**两个**真实FFI exports`wbd_m0_win_game_native_v4_start`和`wbd_m0_win_game_native_v4_tcp_control`，再允许真实Wintun/驱动。旧Game/FEC场景不会额外开启V4/分流；一个原Action只测Game4 off/4lane/CN代表，不恢复全矩阵。
- H2021 Normal实际eth0密文padding抓包为另一SOURCE单独Action，两者网络进程/VM不同。原被跳过Action保留SKIPPED，不造PASS。
```feature-impact
{"kind":"none","ids":[],"reason":"H2022 enable existing Game4 CN explicit native test scheduling and original Rust m0_v4_probe export ABI; product packet logic unchanged."}
```
