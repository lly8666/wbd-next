# PLAN029B H2085｜修H2084首个CI边界，保留未验资格

本批在现行main SOURCE `45fc57cfd9985ce79e437205c2a17062dd6b08ec` 上按真实Action反馈：H2084 原Go/WinForms CLI 源码构建 `44047000912`、native ABI `44047000808`、跨ABI `44047000811`、native functional `44047000779` 等PASS。真实Windows原生H2083 `44045024679` 曾在Ready前因无V3 DLL导出FAIL，H2084已改成默认发布DLL编译`m0_v4_probe`并在签名driver前PE校验，但H2084当前没有获得新的真实原生网络资格（cheap gate阻断），不抢跑或假报PASS。

H2084 三项首故障：`44047001012` 的老 `tests/test_m0_native_ci_scope.py` 仍只寻找旧"条件追加 m0_v4_probe"字符串，因缺substring而IndexError；H2085更新为**必须无条件包含V3发布特性且Windows实际PE export check无条件在driver前**，保留旧试验和产品场景运行时选择核对。Windows Rust component `44047000813` 新普通CN UDP实际A/TTL测试引用`DnsAResolution`未导入，编译E0422；仅用全限定Rust类型名修单测，不修改DNS结果。治理 `44047000928` 合计热文件32893字符超出32768上限；H2085仅把旧H2082/H2077独立文档移出热引用（文件及旧证据全留），新cursor热引用五项定界。

本提交**不改变网络协议、TLS/密钥、OS/WAL门或产品数据面**；新SOURCE签名B0/B1/B2/B3/B4/B5仍待真Windows2025↔WSL2和原GUI/数据/Stop回执；H2077旧源码ordinary三场PASS_SCOPED不借用为029B绿灯。逐个实测首故障修，不额外启动028/030旧矩阵。

```feature-impact
{"kind":"none","ids":[],"reason":"H2085 tests-only Windows Rust type path, CI source-scope invariant and bounded M0 cursor; no product feature behavior altered"}
```
