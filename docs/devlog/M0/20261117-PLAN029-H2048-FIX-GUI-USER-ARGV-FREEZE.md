# PLAN029 H2048｜原始 GUI 场景首个断点：H1845 转参前参数冻结

- [H2045原签名原生Action43994188290](https://github.com/lly8666/wbd-next/actions/runs/43994188290) 当前source969da57 Windows/WSL2 native job FAIL：真实原 WinForms compile + Go/Rust DLL SHA检查 PASS，随后 Python 在启动GUI前拒绝原H1845 `--split-enable` 参数计数，因为 args 刚换成 GUI exe+根目录+seed，自然不再含 CLI 参数。此异常前真实Windows app网络和OS Applied NOT_RUN，旧失败完整保留。
- H2048 仅把“Go子进程真实用户配置源”冻结为 `tuple(args)`，保留原H1845 exact CN/直连地址、真实server/物理source和 CI trial-off 执行约束；GUI仍用自己两个参数启动，且必须真实Go config/OS MTU/owner/双出口/Stop全部通过。并未在应用状态或Rust中伪造PASS。
- H2047同端点TCP53独立场景在途，不重派。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback"],"reason":"Fix fixture-only prestart original child CLI provenance after replacing argv with real GUI; no product admission weakening or false native receipt."}
```
