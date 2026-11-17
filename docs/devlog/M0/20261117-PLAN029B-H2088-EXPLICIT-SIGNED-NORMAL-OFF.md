# PLAN029B H2088｜显式一场新SOURCE签名Normal／业务分流关闭验证

H2087 `SOURCE=2f1b0bac6701a985fc5aa31960bedd2425a5e02b` 完整廉价范围/装配单测及Windows Go、Windows Rust、Linux Rust自测均PASS（Action [44051962624](https://github.com/lly8666/wbd-next/actions/runs/44051962624)），但仓库正确把仅修改测试与治理的提交认作非Native diff，昂贵`native-public-two-os`仍SKIPPED。因此不能声称已经复测H2084默认DLL的真实V3导出。用户明确授权029B，H2088在原`m0_native_ci_scope.py`新增**唯一显式**`[plan029b-normal-off-smoke]`触发，且用同一旧测试模块确认带该commit marker才会调用真正的Windows/WSL2 native job。提交消息带该标记；依然经过所有廉价门，不跳过任何OS/TLS/密钥/SOURCE/签名资格，不选择旧029的Direct场景或028矩阵。

本场先测真实原Go默认`--split-enable=false`、Rust V3应用/UDP/TCP、Signed Wintun+Npcap、OS/WAL回执及owned Stop，**只作为B0下游真实Tunnel基础代表**。受管DNS A/AAAA UDP/TCP53、普通/高级CN、Windows IPv6混合发包、同VM短A/B均需要后续小范围独立证明，不能因这场绿灯写成029B B0–B5 PASS。

H2087治理 `44051962306` 仅旧热文件预算32923超32768；H2088移出旧H2084热引用（旧文档及FAIL证据留库，允许从本日志追溯），保留方案/提示词与本次证据共四项。旧H2083实网`44045024679`缺V3导出FAIL仍留存。

```feature-impact
{"kind":"none","ids":[],"reason":"H2088 source-locked CI explicit one-shot 029B Normal/off real smoke and bounded governance refs only; no product data-plane feature change"}
```
