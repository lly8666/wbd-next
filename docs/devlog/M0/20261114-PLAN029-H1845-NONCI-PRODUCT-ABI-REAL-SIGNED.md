# PLAN029 H1845｜用户真实 `--split-enable` 的单独 SOURCE 签名验收（不同于H1844慢TCP）

- H1841 signed `b7e947a` [Action43597050204](https://github.com/lly8666/wbd-next/actions/runs/43597050204) 真实Windows+Linux原Go/Rust编译成功，MTU1460配对成功，但客户端未达READY，首故障`Failed to find wbd_m0_win_native_v3_start procedure in ...wbd_engine.dll`。正式产品选项在非CI子进程启用时，工作流只为私有`WBD_PLAN029_NATIVE_V3_TRIAL=1`构建`m0_v4_probe`导致导出缺失。因此已在H1843 SOURCE`29ec318`修正为**试验或正式产品**任一明示场景都要在当次release DLL编入V3 ABI并预先真实GetProcAddress证明，运行时分流仍只认用户`--split-enable`。
- H1844 [Action43598740573](https://github.com/lly8666/wbd-next/actions/runs/43598740573) 已在独立SHA`ecd85c18`通过Windows+Linux Rust/Go单元/装配门，后续签名P2/Stop尚在进行；不在本H1845再起P2。
- H1845只修改现有真实Windows/Linux `tools/m0_wl_public_normal_e2e.py`正式CN冷启动夹具（源路径命中workflow `push.paths`），在启动前额外验证且打印不泄密标记：原Go用户参数`--split-enable`恰好一次，`--cn-rules-file`恰好一次且是**当前源构造的实际绝对owned CN文件**`cn.example\n`；子进程`GITHUB_ACTIONS=false`、`WBD_PLAN029_NATIVE_V3_TRIAL=0`、旧`WBD_PLAN029_CN_RULES_FILE`不存在。静态测试同步检查源契约。此证据只是启动前契约，绝不作为OS Applied/真实业务PASS。真实原Go认证TLS/Rust Wintun Npcap接线、DNS/Direct TCP UDP/Tunnel、独立Windows Linux owned Stop继续由同源真实现有验收代码执行。
- 此提交仅`[plan029-real-product-cn]`一次专用标记，不混`[plan029-v3-real-p2-rebuild]`；新Action为独立SOURCE，各自真实签名时序、清理，不把P2性能与正式产品入口混成一个实验。H1845正式CN网络/Stop **NOT_RUN** 直到该源独立Action的终态。
- P2旧真问题仍OPEN：H1839物理1MiB 297ms vs Direct上传18.969s/下载38s未全；H1843 TCP有界FIFO/Wintun背压正确性修复后以H1844签名场景验证，不可从组件测试直接宣布达标。Game4 CN/IPv6、GUI真按钮/Stop、FakeIP慢fsync/Compaction、P1 CPU亦OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Add source-locked non-CI user CN product launch invariant in existing native two-OS harness; no production protocol behavior or OS ownership changes."}
```
