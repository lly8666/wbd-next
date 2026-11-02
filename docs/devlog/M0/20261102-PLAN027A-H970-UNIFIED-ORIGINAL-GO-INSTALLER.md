# PLAN027A H970｜排除MSS同源装配阻断，不改产品实现

恢复main `c1945a68835bae48b16634bba76f292f4f5f8435`、cursor和Actions：H968 [41480121662](https://github.com/lly8666/wbd-next/actions/runs/41480121662) Windows Go正式编译、SYN/SYNACK编码测试、Windows/Linux Rust单测均PASS，但Linux原Go编译前安装器因重复的旧hash表拒绝`packet.go`（旧表4dd669...，现行manifest/result blob为82d462...），导致整run FAIL。H969 [41480968817](https://github.com/lly8666/wbd-next/actions/runs/41480968817) 正确依赖这个失败Build而拒绝复用，保持FAIL，不重复运行无价值模式。

此次删除`tools/m0_install_public_faketcp.py`内第二套手填original/result hash，Linux及ARM64现在和Windows装配用同一个`manifest-plan020-m0.json`七个原Go FakeTCP文件，逐个校验原始SHA、现行result SHA、路径、create/replace、完整集合，**全员先验证才写到Action的临时原Go checkout**。添加`--check-only`和单测，在Cheap CI先证明无漂移。没有改Rust唯一冷预算、Go握手产品字节、编译出的ABI，绝不保留固定1360协议分支或新legacy选项。新源码Native的真实1420/1420与1389/1389仍NOT_RUN；已失败H958 DF另保留，不混入本任务成果。

```feature-impact
{"kind":"none","ids":[],"reason":"Unify Linux/ARM64 source-pinned FakeTCP installer with authoritative Windows source assembly manifest and exact seven blob checks; no product algorithm or feature status promotion."}
```
