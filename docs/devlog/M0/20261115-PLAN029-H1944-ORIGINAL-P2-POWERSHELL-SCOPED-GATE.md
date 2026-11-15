# PLAN029 H1944｜在真实Windows编译前修正H1943的PowerShell嵌套门

- H1943把新的原 Rust TX 外层回包读取ready票据年龄（≥8/16ms、max）及同轮内层 WinSock write 的七个聚合计数加入已有源锁P2诊断，商品转发路径/ABI/owner不变。代码审查发现`.github/workflows/m0-wl-public-normal-full.yml`在新分支末尾原有`Write-Output PLAN029_H1943...`之后多出一个结束`}`，可能提前结束P2_MIXED源锁的PowerShell原生资质门。此错误不是应忽略的Action假红；必须在昂贵Windows原生跑前修复。
- H1944仅删多余的**一处**结束括号，保留H1942 384 FIN-first+384 payload-first SHA/FIN/owned Stop严格验证和所有旧H1898 10GiB/500/700Mbps、其他D1–D5门。新增廉价Python单元测试精确检查新H1943支路到H1898支路之间只有一个闭合，并拒绝多余闭合回归；不碰原Rust行为。新源码在真实原Win2025+WSL2签名后才能称新聚合诊断通过。
- 上次真实H1942 Action43751965403 源`cbf01fa` SUCCESS，Direct64B回包p99 15.568ms (FIN-first) vs15.729ms (Linux payload-first)，非FIN等待唯一原因，原签名证据仍有效，但H1943/H1944改动尚没新SOURCE实机收据。PLAN029 P1 all/CN/CN/all四臂和CPU因果A/B、Direct p99优化保持 OPEN。
