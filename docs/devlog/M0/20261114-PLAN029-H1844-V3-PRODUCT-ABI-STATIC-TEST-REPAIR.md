# PLAN029 H1844｜修历史静态 V3-only 断言并重启一次真实P2

- H1843 SOURCE `29ec31846c236f16a476ea6d3860d4950f9cf516` 的源码已经保留了真实TCP回程有界FIFO邮箱重试、Wintun ring背压保留和显式CN正式产品V3 ABI构建门；`m0-wl-public-normal-full.yml` Cheap workflow Action43598580600 失败于已有`tests/test_m0_plan029_h1749_signed_direct_order.py:test_h1820_real_source_built_v3_export_before_signed_native_driver`：旧静态断言字符串只能是 `if($env:WBD_PLAN029_NATIVE_V3_TRIAL -eq '1')`，且不允许增加正式用户CN源条件。此时Windows/Linux native jobs被正确跳过，**H1843未运行网络P2、也无Stop结果**。
- H1844仅修改旧测试以匹配真实构建契约：V3 ABI由私有签名试验 **或** `WBD_PLAN029_PRODUCT_SPLIT_SCENE` 使用；导出在真实Npcap/Wintun安装前仍强制核验，临时借用旧DLL继续禁止。原`--split-enable`用户开关/非CI child `GITHUB_ACTIONS=false` 不变，绝不让product编译标记默认为用户启动意图。
- 本SOURCE只带唯一`[plan029-v3-real-p2-rebuild]`标记、由现有source fixture路径触发一条签名Windows2025/UbuntuWSL2同VM正常/Direct1MiB＋全程小Tunnel UDP，量化H1843修复后速率/首回包/CPU公平性/双方owned Stop。提交时这些新网结果仍**NOT_RUN**，不复用H1839的性能收据。上一真实a50 P2仍FAIL：物理297ms，Direct上传18969ms、37.172s收917504B。
- 已独立通过的H1842治理/维护门保持；下一单独SOURCE产品真实开关`[plan029-real-product-cn]`在H1844成功编译后另行验证，避免与P2混场。Game4 CN/IPv6/GUI真Connect Stop/P1/慢fsync仍OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Repair an obsolete static check that assumed V3 native ABI could be linked only for private trial; preserve source-locked actual signed P2 product behavior and official cold --split-enable separation."}
```
