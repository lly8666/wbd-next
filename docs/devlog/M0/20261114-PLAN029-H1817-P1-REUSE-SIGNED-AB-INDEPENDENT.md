# PLAN029 H1817｜P1从已编译的相同成品再次运行同VM A/B（与P2并行）

- H1816 已修 Linux WSL2 `-u root` UDP程序`source:null`造成的假FAIL，保留 Windows GITHUB_SHA 硬断言、Linux同一场景hash与原Rust/Linux产品manifest证据。H1814 A腿真实原始Windows↔WSL2 50Mbps两向正常、tc和UDP/TCP Stop PASS，B还未进入，故P1整体不能记绿。
- 本H1817`[plan029-v3-real-p1-tunnel-ab]`选择唯一60s中等50Mbps/25ms/0%双向方案，`[plan029-v3-real-p1-reuse]`按H1814 Action43571086653相同编译SOURCE `c262636c81d688e8df8e844b668bbcc57957425d`和 manifest SHA恢复Windows EXE+DLL/Linux GoRust server，产品目录 git diff 清零；原先已绿Windows/Linux x86、ARM64纯组件不重跑。A旧V4/Stop→B新V3 route=all/Stop严格同一 VM 顺序。后台无定时任务、不同P2 Windows Runner独立Actions真并行。
- 增补静态门：验证 P1 协调器源码的A/B固定顺序、同二进制hash、Windows应用SOURCE、Linux WSL只允许null/本次SOURCE、Linux binary SOURCE一致、实业务CPU/交付GiB、RTT p99与双方Stop。新测试只改test/cursor，不改产品/签名驱动/网络协议。
- 真正H1817 P1和H1816 P2尚待对应Action的结果；5%成本线仅提示，不因VM噪声反复极限测。

```feature-impact
{"kind":"none","ids":[],"reason":"Source/manifest-pinned independent P1 re-run trigger plus static source/provenance gates; no product code modified."}
```
