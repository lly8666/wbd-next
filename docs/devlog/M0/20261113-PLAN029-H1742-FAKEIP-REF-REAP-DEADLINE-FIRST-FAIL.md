# PLAN029 H1742｜FakeIP活流回收真Windows首FAIL：测试钟点早999ms

- H1741 SOURCE `23e56deb0c255aa4ea5a04bb1d5b75764dfc6402` [Win/Linux Rust Action43411970374](https://github.com/lly8666/wbd-next/actions/runs/43411970374) Windows **58 PASS/1 FAIL**、Linux PASS；[GNU cross ABI43411970273](https://github.com/lly8666/wbd-next/actions/runs/43411970273) 和治理43411970191 PASS。不能把总Action FAIL改为绿灯。
- 首错`plan029_native_fakeip_real_business_ref_survives_ttl_and_retires_exactly_once`：活流在wall epoch 602100扫描后，`FakeAllocator::reap_due`按原安全设计再延后**60000ms**，因此要662100才可回收。新增测试把661101误当作到期；观察实际0是正确的。不改真实产品算法，只增662099仍0、662101回收1的明确边界；重复retire无引用下溢仍保持。
- 同一Rust NativeOwner real FakeIP五元组ref生命周期、新物理UDP退场事件没有回退，继续待新SOURCE Windows CI。产品仍欠Defender当前代精确Allow/Post-Apply TCP授权、真双DNS/Direct/Tunnel网络、D1-D5/P1-P2/GUI live/padding。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Correct first source-locked Windows FakeIP live-ref test's deferred 60-second reap deadline; keep unchanged native behavior and historical FAIL"}
```
