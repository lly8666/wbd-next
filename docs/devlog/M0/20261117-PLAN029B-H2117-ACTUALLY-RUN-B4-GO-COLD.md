# PLAN029B H2117｜B4 original Windows Go 三代冷测试从「只编译」升级到「实际执行」

H2116 SOURCE `a560d3514480e1937a39a5c037dbb6dea643fe6d` 的 [M0-WIN-LINUX Action44120844855](https://github.com/lly8666/wbd-next/actions/runs/44120844855) 原cheap、Windows Go、Windows Rust、Linux Rust**全部SUCCESS**，原生两个OS工作有意SKIPPED（本批未启B4原生场景）。Windows Go artifact14346440193 ZIP SHA256 `e890cb021387185ce1d0694f3a6e3c8b0b6f47aef47847a2e6c0ecdadb1223de`、3成员CRC全PASS，`preflight.json.scope=GO_COMPILE_ONLY`；Windows Rust artifact14346250607 ZIP SHA256 `f2076a0fedd47db09ef48440db205a9dbbfd5a3fff09346adc01525af8feca23`、2成员CRC PASS。H2115原装配SHA错的FAIL已保留，H2116只修1个manifest pin后源码锁编译绿。独立原H1661 Windows编译Action44120845123以及治理/功能目录Action44120845001也成功。

**不能把Go编译算作H2115新增B4 Go纯测试通过。** 原流程只运行`go test -c`，相应client.test.exe中的`TestPlan029BThreeGenerationsAdvancedOrdinaryAllNoStaleWriter`尚未执行。H2117给**已有Windows Go预检**在`go test -c`紧邻位置新增精确`client.test.exe -test.run=^TestPlan029BThreeGenerationsAdvancedOrdinaryAllNoStaleWriter$`与原退出码硬门；不另建Windows编译job、不装Npcap/驱动、不跑GUI伪造OS Applied。新增静态回归保证执行器确实调用三代测试而非仅链接；Rust三代旧FakeIP防漏相关单测继续跑Windows/Linux原库。H2117当前仅派发廉价测试工作流，不派发B4签名场景。B4实际WinForms先进CN→普通CN→all三次独立Stop、旧假地址真实socket不出机、晚回调、Game2/4另行资格；B5 <=10Mbps同VM CPU/GiB/RSS/p99未验。029B/029不收口，030不开。

```feature-impact
{"kind":"none","ids":[],"reason":"H2117 only makes existing compiled Go B4 three-generation cold test execute within original Windows preflight; no product code or feature-status change"}
```
