# PLAN029B H2097｜收H2095真FAIL：双重转义拒绝真实CN DNS；只请求一次新签名B2

H2095 [Action44074535313](https://github.com/lly8666/wbd-next/actions/runs/44074535313) 原始签名Win2025 Wintun/Npcap↔WSL2，SOURCE `aa53d4b3b73d57d993f5bb0da1f29e8cc54462ef`；完整artifact14325645963 SHA256 `311d822575373c4b050cf955871cfd682e153744083e301621b895e3e7e13b43`。实际guest物理CN DNS监听见源172.20.32.1、QNAME `www.cn.example` A、头`000101000001000000000000`，**查询字节正确**，但H2095测试夹具误写 `b"\\\\x01\\\\x00\\\\x00\\\\x01"` 双重转义导致无条件拒绝；原Windows脚本随后收到ID6201、QNAME保留、rcode SERVFAIL(`8182`)。这是明确的首个fixture错，不是源路由确认失败。本次原Go finally `M0_PLAN027_NATIVE_STOP_RESULT ... PASS`，但完整B2及既有双向TCP45902没有跑到；Action仍**FAIL**，旧H2093/H2094 FAIL保留。

H2096 `ad86b55f4b206484d68a724634bc67e4c3ac661c` 已修正原夹具字节与AST静态回归；[Action44074889319](https://github.com/lly8666/wbd-next/actions/runs/44074889319) 廉价门、Windows Go/Rust、Linux Rust均PASS；由于该源码提交没有显式原生标记，签名步骤正确SKIPPED，不能声称复验通过。当前唯一必要下一步是新SOURCE **一场** `[plan029b-b2-cn-ordinary-real]`：先CN直连DNS与非CN Tunnel DNS共享海外真实A/CNAME/TTL2和两次实际Tunnel UDP；继续不删既有Linux↔Windows原内核双向TCP、精确测试自有45902 ACL和owned Stop。场景内唯一产品与唯一owner，快检先行，不触发其它029旧P1/P2/028弱网矩阵；新场状态先记NOT_RUN。

B2高级CN FakeIP、B3真正Windows发IPv6混IPv4、B4多代GUI/Stop/Game、B5同VM10Mbps CPU/GiB与小流p99分别保持NOT_RUN。历史B0/普通CN局部PASS不可迁到新SOURCE。

```feature-impact
{"kind":"none","ids":[],"reason":"H2097 exact H2095 signed failure evidence, cursor and one originally authorized B2 fixture source-frozen native retry; no production or feature card behavior edited"}
```
