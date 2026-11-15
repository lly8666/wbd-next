# PLAN029 H1886｜四次真ABBA业务完成后 finally 局部变量遮蔽导致CI FAIL

- [H1885 Action43669531835](https://github.com/lly8666/wbd-next/actions/runs/43669531835)，Windows原始Go、Rust release、签名Npcap/Wintun和WSL2真环境前置均通过。子进程原产品先打印`PLAN029_H1884_SAME_VM_SAME_BINARY_COPY_VS_BYPASS_ABBA_AND_OWNED_STOP_PASS_SCOPED`及`WBD_WL_TRUE_PUBLIC_MODE_WIN_LINUX_DUPLEX_STOP_PASS normal`，说明四次真Direct测试走到原owner验证分支；但原 E2E 进程在 `tools/m0_wl_public_normal_e2e.py:2425` 的finally抛`AttributeError: 'str' object has no attribute 'close'`，所以**主真实业务Action结论是FAIL，最后report.json缺失，尚不得发布A/B数值为验收**。
- 第一个错误不是TCP/UDP/Rust或Stop，而是H1884新加的`logs=(out/"client.log").read_text(...)`覆盖了最外层保存原文件句柄的`logs`列表；finally原有`for log in logs:log.close()`因此遍历字符串字符。H1886只改临时变量名为`win_diag_text`并更新日志包含判定，新增静态回归保证文件句柄列表不会再被覆盖。Rust算法、private probe选路、四条payload、两个方向队列和防火墙/OS恢复完全不动。
- H1885原FAIL保留，H1886按新SOURCE走同一只读新Linux对端+原Windows signed CI，不重复派旧SOURCE。真实同VM A-B-B-A改善需用**完整新签名Action SUCCESS+最后report+owned Stop**才可讨论，驱动CPU/P1+9.41%另行OPEN。029仍IN_PROGRESS，028/030未扩。

```feature-impact
{"kind":"none","ids":[],"reason":"H1886 repairs only accidental Python file-handle list shadow after otherwise completed signed ABBA; no product code or feature card update."}
```
