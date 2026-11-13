# PLAN029 H1757｜真实Defender COM单主机读回第一差异
- H1756 SOURCE `df999a2b3970d0c91c960a372189e435acd93976` [Windows Action43440902371](https://github.com/lly8666/wbd-next/actions/runs/43440902371)：original Go装配/编译 PASS，真实单条Defender COM Add/readback仍FAIL。精确首错 `LocalAddresses got="10.234.12.34/255.255.255.255" want="10.234.12.34"`；原COM finally CAS仍未确认、WAL保留。不能宣称产品或规则全清理。
- H1757只在Local/Remote address域等价接受**完全相同IPv4单主机**或该IP加`/255.255.255.255`，反例拒绝网段、列表、任意匹配；未扩大Allow。原intent/owned/foreign CAS不改，Go overlay和manifest两个源SHA在同一提交。
- H1756 [Governance43440902708](https://github.com/lly8666/wbd-next/actions/runs/43440902708) 功能卡超过16KiB FAIL；本次只压缩重复历史说明，保留已有Action/evidence文件，029范围仍OPEN。下一步收自动CI第一真实差异，不重复旧网络诊断。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Source-locked H1756 real COM /32 readback FAIL and H1757 exact-host-only patch plus 16KiB feature card correction"}
```
