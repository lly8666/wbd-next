# PLAN029 H1838｜修GUI导入后路径断言，不删除便携安全隔离

- H1837 SOURCE `33e2f79352469d62e3025176670fd03d450e554a` [Windows real WinForms+Go CLI Action43593094295](https://github.com/lly8666/wbd-next/actions/runs/43593094295) 完整原Go/Rust DLL/WinForms构建成功；真GUI清单**59/59键一致**；已有Normal`split-enable=true`、文件在Root内转换为绝对路径、真实`--check-config`回读、规则缺失拒绝、Game4 CN早拒绝、默认1460/显式1500/单DNS旧兼容等均已PASS_SCOPED。失败发生在程序末尾`H1835_reopened_CN_split_opt_in_and_owned_file_still_saved`一项测试断言。根因并非GUI掉开关或真实CLI参数丢失：`PortableStore.ImportValues`将此前导出配置内的绝对CN文件复制到专属`data/cn-rules-{profile.Id}.txt`（正确的便携导入与owner边界），不保留原`data/h1835-cn-domains.txt`的路径。旧断言错误假设导入不改文件名。
- H1838只改源锁WinForms CLI夹具：断言重开后`split-enable=true`，规则源为`data/cn-rules-{id}.txt`且真实文件仍含`cn.example`；再次使用**当次原Go `ClientSession.ValidateAsync`**验证新路径的精确绝对值，无模拟OS Applied或跳过原导入迁移测试。此批H1838 GUI Action**NOT_RUN**，结果待CI；若失败定位下一个首边界。保留H1837原失败。
- 另一路H1837 [真实签名P2 Action43593094309](https://github.com/lly8666/wbd-next/actions/runs/43593094309) 在此提交时Windows/Linux组件已成功，源锁Windows+WSL2实体尚在准备中，**P2网络耗时NOT_RUN**。本H1838提交不带P2 marker，不为同一场景重复起网。
- 明确边界：GUI/CLI`--check-config`仍只是**配置读回**，真实Windows signed Wintun+Npcap产品OS Applied/Ready/Stop及D5尚未验收；Game4 CN owner、IPv6旧策略、P1 CPU、P2性能、FakeIP慢fsync/compaction interrupted仍OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Test-only fix of expected portable CN rule snapshot filename after ImportValues; preserve existing correct owned file-copy behavior and independent signed P2 source lock."}
```
