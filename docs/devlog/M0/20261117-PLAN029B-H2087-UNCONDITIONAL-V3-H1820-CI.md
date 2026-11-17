# PLAN029B H2087｜H1820旧场景测试接入默认V3发布资格

H2086 `SOURCE=69cdf7efc45425114e7d692f4598427cda74bac2` 的廉价Action [44051188600](https://github.com/lly8666/wbd-next/actions/runs/44051188600) 已确认 H1843/H1859 以及其后Python IPv6/QPC许多源锁测试PASS，但到旧 `tests/test_m0_plan029_h1749_signed_direct_order.py::test_h1820_real_source_built_v3_export_before_signed_native_driver` FAIL。该H1820断言仍要求发布DLL按私有PLAN029场景`$features+=',m0_v4_probe'`，还要求早已改名的`PLAN029_H1820_ACTUAL_WINDOWS_DLL_V3_START_EXPORT_AND_LOAD_PASS`。这会错误阻止029B关闭业务分流仍使用Rust V3公共DNS/Normal启动填充，后续昂贵签名原生实际未开始。

H2087只修该现有测试对**真正新行为**的资格要求：发布`$features='m0_v4_embedded_go,m0_v4_probe,fec2_product_record,native_fec_acceleration'`，绝不条件追加V3，WinDLL实际`getattr(d,"wbd_m0_win_native_v3_start")`，且新`PLAN029B_H2084_ACTUAL_WINDOWS_DEFAULT_V3_DLL_EXPORT_PASS`必须发生在原Win Wintun/Npcap驱动安装前。旧 P1/P2/Game4场景选择仍需原显式条件、未删除。编辑前按源锁字符串逐项核验9条断言都成立，并检查后续28个廉价测试模块对撤销的V3增量/旧H1820标记无引用。

产品Rust/Go、TLS/WAL/owner、防火墙门均未改。此前真实H2083 Action44045024679的缺导出FAIL和旧H2077签名Normal PASS_SCOPED均独立保留。**H2087新同源码真实B0–B5仍未验**，不得以静态门结果冒充原生产品可交付。

```feature-impact
{"kind":"none","ids":[],"reason":"H2087 only migrate obsolete H1820 CI contract to default release Rust V3 PE invariant; no product code or feature cards changed"}
```
