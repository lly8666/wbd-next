# PLAN028 M0 H1608｜用户跳过H1602近MTU；并行复用同一套Linux native ISA-L正式产物

用户要求：跳过同类Windows WSL near-inner-MTU，不继续重复；**复用编译产物并且不同Action并行**。H1607历史失败保留为原生预环境阻断、真实nearMTU业务NOT_RUN，用户明确本轮SKIP，不推定该硬门合格。

新增三份workflow：可复用的唯一原真实场`.github/workflows/m0-plan028-h1608-prebuilt-native-path.yml`＋两个push触发器，各有自己的独立Action和Ubuntu x86_64 runner，在同一提交同时触发。一个模式Normal/FEC Off/Auto租约/物理源10.25.0.2→10.25.0.3、外物理MTU1500→1280，真Go TLS→Rust M4→OS、路径B认证后旧A Stop与切后5次真OS UDP。另一个Game4显式fixed6/Auto租约/物理路径变化、原TLS八个四lane两代的ClientHello、真FEC parity/共享TUN、A+B→B及5次真UDP、各旧owner Stop。Game4固定强度**只是此测试显式选择**，产品默认仍FEC Off、outer1460；不改代码/GUI。

两个场景都从原成功 SOURCE `8a31375e36bb6a93860c5579e64b4a39d0b6e346` Action `43027983611` artifact `m0-plan024-linux-product`获取原Go client/server及Rust ISA-L so，内嵌证实 `rust_native_fec_acceleration=true`、原Go commit、ISA-L源码、架构和三个SHA256：client`7f347ae9dc878edf508aa5fdeb8668ccae653682d01898435b69d42c94a555d1`，server`9188f3941eba3dfd48831f779e0d8b73d3b31deda4c1978a1f270e11d75dcc71`，Rust so`2947d148d325e198acd920c56803ad168175ba11590396478682693fcf5922dc`。当前main到原SOURCE shipping`crates/r0/Cargo/prepare_windows_wiring`以及原真实netns fixture要求零差异；若改动则拒绝复用，绝不暗中降级scalar。两场没有cargo/go编译、没有Windows/WSL、没有重跑150秒或1800秒。

当前提交仅派测试，未返回真实业务/Stop前都是NOT_RUN；异常记录环境和产品首错，不能冒充业务PASS。每个Action上传原始原生日志和有效值JSON，结果需要另行收齐。原H1601同账号五端150秒和H1604的真实轮换可直接复用，用户排除多Wintun的历史H1587 FAIL仍保留。

```feature-impact
{"kind":"none","reason":"H1608 only two separately scheduled native CI smoke scenarios reusing verified product artifact and source guard; no shipping product, default, or GUI change."}
```
