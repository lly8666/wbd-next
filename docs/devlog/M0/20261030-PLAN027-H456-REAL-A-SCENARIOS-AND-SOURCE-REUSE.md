# PLAN027 H456｜实际A2/A3单场景双OS source复用和现有冻结清单负例

H455 PRODUCT SOURCE 88ba090086f0e42b4909d504bde3523848e414a3 的 Linux combined original-Go/TUN业务真实Action40993452494 PASS，Windows real Wintun五模式Action40993452408 PASS，Windows↔Linux Normal native run40993452459尚在途，保持原失败或成功由其后决定。本批**不改任何crates/r0/Go功能源码**，二进制Source仍为H455，不重编译；当前HEAD变化仅测试/装配/Action脚本。

修H455 governance-maintenance Action40993452425 两处旧Go overlay blob pin，历史M4 PINNED_FILES未动；当前live result_blob分别为4b1a9076和aada7132。

新增 A2 Normal/off 0%及30%、A3 Fixed最高档30%，每方向10Mbps、250ms原生netem、60s独立场景、同packet mix/固定seed、有界MTU与Stage。三条分别独立GitHub Actions job（不拼同VM测量），仅在H455真正Normal双OS全Action PASS和原SHA Windows+Linux二进制两份artifact存在后发出；30%原生loss场景不得错误套用clean99.9%第一到达门。Actual R/F、R/(F+R+C)、真实UDP/TCP/p99/owned Stop由各Action观察决定，不伪造。

允许source-verified 1模式Fixed V2复用；H456 coding-only主push跳过重复OS构建；H455 B dispatcher改为只要产品crates/r0/manifest完全未变，即允许最新harness HEAD与冻结二进制不同，以便B独立模式同SOURCE重用。A4 sustained Auto、A5同VM CPU、B全生命周期、C容量/5min仍须后续。

```feature-impact
{"kind":"none","ids":[],"reason":"Source-verified A2/A3 scenario/Actions assembly plus live Go overlay fixture hashes; no binary product changes."}
```
