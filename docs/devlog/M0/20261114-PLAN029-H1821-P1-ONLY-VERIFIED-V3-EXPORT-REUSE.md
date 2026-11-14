# PLAN029 H1821｜只在H1820 V3真实ABI导出和同源二进制产物存在之后激活P1

- H1820 SOURCE `b7b688573326580e39571c1e748663b8566d5fc2` Windows2025 真机release固定`m0_v4_embedded_go,fec2_product_record,native_fec_acceleration,m0_v4_probe`，构建后通过 Windows WinDLL 真实导出 `wbd_m0_win_native_v3_start` 检查。H1821不再允许P1/P2自动选择原H1814 SOURCE c262缺V3符号的DLL；变更指向 H1820 Action43574002456 实际重新编译的 Windows EXE/DLL 和 Linux GoRust server。
- 保留GitHub run head sha、Git产品目录 diff、来源manifest、每文件SHA256+size强验证，且**再独立用当前 P1/P2 Runner实际加载此DLL检查V3符号**才允许安装原Wintun/Npcap及跑产品。新增专门静态合同，禁止c262旧资源出现在当前P1/P2自动复用环境。原未知feature仍拒绝；不替换产品源、不关闭Defender。
- H1821只添加CI/测试/状态。只有H1820双方产物真正上传才允许H1821进入main触发Action。P1两腿必须同一个VM顺序A旧V4→Stop→B V3/all→Stop；H1820 P2独立WindowsVM相互并行。待真结果后仍需Game4实际分流、IPv6 OS和GUI-origin signed网业务验收。

```feature-impact
{"kind":"none","ids":[],"reason":"Use only source/manifest/hash/export-verified H1820 V3 Rust DLL and unchanged product binaries for independent P1/P2; no compiled product code alteration."}
```
