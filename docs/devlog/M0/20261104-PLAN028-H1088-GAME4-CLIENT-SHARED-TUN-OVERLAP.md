# PLAN028 H1088｜Game客户端以既有Rust单TUN reader做重叠交接

H1087 route-key/WB-R1前导移除限定收口之后继续原PLAN028。过去 Game auto-IP客户端使用group专用TUN reader，新出口通知必须先Stop旧A再开始B TLS，业务必断。现在复用原Rust `SharedTunReader` 单读者：原 TLS验证后每lane真实受保护/32先OS应用/读回再绑定Rust，客户端以保留的默认零地址route索引、服务端以其已验证/32分发；新B完整TLS、MTU/readback、真实Game M4 Ready时原Rust按generation原子发布新default，旧A只有随后才Stop，旧generation回收不能删B。Go只负责原生通知/冷TLS和generation，不逐包转发；Rust FEC6/record/AEAD/PN/稳态wire不变，正常外层默认1460。

同SOURCE新增一个Linux x86_64 client+server真netns Game4 fixed6场景：原Go TLS 4+4各自一条到443，物理源IP .2→.3及MTU1500→1280、相同认证/32、双端各一名Rust reader、旧新FEC parity，真实后续UDP和Stop，精确证“B候选→新B READY→旧A Stop”，同时从SYN抓8条ClientHello且无WB-R1。本次是**IMPLEMENTED_NOT_TESTED**，真实资格只由新Action确定；结构上的overlap不等于零丢/CPU p99。下一整个Linux任务原生ARM64双端。Windows物理网卡切换、完整TLS Finished/标准基线仍OPEN；H998在线MTU缩窄FAIL、旧ARM64 Game4FEC Action FAIL、远端ICMP/CPU因果未证不更改。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1088 reuse Rust shared TUN native one-reader for authenticated Game client, B TLS+MTU/M4 Ready before old A exact Stop; x86/x86 Game4 native scene pending."}
```

## H1089 原装配窄修（同产品源码）

[首次定向 Action41765630079](https://github.com/lly8666/wbd-next/actions/runs/41765630079) FAIL_PRE_BUILD：源锁 `assemble.py` 成功完成原 Go manifest 后，夹具又调用 `m0_install_public_faketcp.py`，其 donor-original 检查必然拒绝已替换的 `packet.go`。只删除**重复安装**，保留原 SHA 校验/版本/场景，Rust/Go 产品文件零变更。H1089 完整原生结果仍待新 Action，未报 Game overlap PASS。

## H1090 源角色边界极窄修复

H1089 [Action41765851943](https://github.com/lly8666/wbd-next/actions/runs/41765851943) 原Go TLS/Game4FEC6/Rust M4 Ready，真实第一UDP回显却TIMEOUT：客户端Rust copied9/delivered0/rejected6/raw_received9/auth_rejected0；server回应已offer。新增Game客户端自身受保护/32用于**出站默认TUN路由**，误被原GameKernelOwner用作客户端**入站服务器源地址**校验，从而把合法server源10.66.0.1拒绝。本批只把 `GameKernelOwner` 的内层客户端源/32防伪限定在server角色；client仍须验证 TLS/AEAD/PN并保留自己的/32 outbound reader权限。H1089真实FAIL原证据见 docs/evidence/M0/PLAN028-H1089-SOURCE1725-GAME4-CLIENT-REVERSE-IP-FAIL-20261104.json；H1090未测，不能冒称Overlap PASS。
