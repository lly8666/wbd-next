# PLAN029B H2082｜B0 独立公共TCP53最小listener + IPv6/IPv4借用公平测试

H2081 新同源 Go H1661编译Action44042989623、Windows Rust ABI44042989392、交叉ABI44042989441、native-functional44042989366及Rust Direct组件44042989598均PASS。旧 GUI no-network Action44042989350 唯一业务夹具红灯为 H1835 期待「Game4+route-mode all，即使split开启也必须拒绝」，但029B有效规则是 mode=all **业务关闭**，因此固定夹具改为读取原Go CLI真实effective all/split=true（未宣称Game4原生CN支持）。governance44042989638 的 scope error 只是 cursor context_refs>8，修为恰好8条。上述FAIL原样保留。

**B0真实资源修复**：原`NativeTcpActor`内已有与业务不同的`dns_nat`及单个原owner实际WinSock listener，`nat:DirectTcpNat`改`Option`。Mode All 创建`nat=None`、无业务Direct socket/NAT/主动连接，仍可在已有 OS Applied 之后用`dns_nat`处理真正应用 TCP53。Go cold All/off 为此分配唯一、按代198.19/16 synthetic /32，不创建业务CN/Direct规则/UDP socket/FakeIP writer；原 exact Defender grant及owned Stop不放松。没有第二个TCP栈、线程、WFP/Go逐包服务或假OS Ready。

**B3 Windows**：在已有`WintunRx::read`上增加测试替身：40B IPv6 Wintun loan必须跳过、不复制到M1、按原API释放；同一借用worker下一次20B IPv4读取成功并释放。此为**真实函数的单元测试**，仍不是物理 IPv6 Windows/Wintun捕获证据。

H2082代码候选尚未跑本源码CI/签名原生 B0/B1/B2/B3/B4/B5，不写PASS。避免旧028全矩阵；按首个新错误继续到最小真实Windows Linux代表与顺序同VM资源/性能证明。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport","gui-config-feedback"],"reason":"H2082 B0 minimal DNS-only TCP listener without business Direct NAT, B3 IPv6 Wintun mixed frame unit and GUI effective All fixture; new source signed native NOT_RUN"}
```
