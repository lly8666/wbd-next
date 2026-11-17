# PLAN029 H1995｜原H1993真Windows/WSL2正常P2失败：正确处理recv跨桶，保留原FAIL

- 冻结SOURCE `34e87006c51db9c8e183af68482050e6550fb460`、[原M0 Action43840543096](https://github.com/lly8666/wbd-next/actions/runs/43840543096) **failure**：native job133210556310在新Python测试器 `normal_tcp_128k_progress_gaps` 首次报 `H1993 TCP 128KiB milestone missing or reordered`。原cheap、Win/Linux Rust、Windows Go、Linux peer builds **SUCCESS**；真Windows/WSL2物理/Direct两条1MiB app kernel TCP、SHA/FIN及96B Tunnel UDP120条业务已实际完成，但**owned Stop阶段 NOT_RUN**，原FAIL不改写。
- 已下载并检查原 [artifact14214065842](https://github.com/lly8666/wbd-next/actions/runs/43840543096/artifacts/14214065842)；原物理每128KiB下载累计字节为 `134968,268152,399224,530296,661368,792440,923512,1048576`，原Direct为 `140296,263583,408275,525661,656733,789154,920422,1048576`。两路SHA一致 `70c482ce452eaf4f6c303008a359e629aecba5dd9d1c44f2123542ea30213586`、应用耗时物理300.860ms、Direct319.608ms；Tunnel真实UDP120条/p99 2.366ms/最大回复间隔17.814ms。这些为**原FAIL Action内的部分有效业务事实**，绝不升级整体成功。
- 第一异常根因确定：发送端每16KiB进度恰会落128KiB倍数；下载端应用 `recv(min(16384,...))` 后才记录跨越128KiB门槛的`len(echoed)`，不一定整数倍。H1993错把下载值要求 `==i*131072`，误拒原真kernel业务。H1995仅允许下载范围 `i*131072..min(1048576,i*131072+16383)`，仍严格拒绝缺/重桶、字节跨越超过一次recv、错误role/时序；上传继续精确，实际下载累计字节原样写入结果而非伪量化。
- 原失败artifact离线纠正后最大128KiB下载交付间隔：物理**0.831ms**、Direct**5.283ms**，仅一轮失败Action的真实应用时间戳，不是2048条RTT p99/纯kernel时钟或CPU因果。新增实际收件八桶源锁正例、越界反例，共9项纯回归；不动Rust/Go、TLS、缓冲、协议或Stop验收。只使用已有workflow原H1815 **一个**[plan029-v3-real-p2-rebuild]正常1MiB+Tunnel UDP，无4MiB、旧2048、highrate、压力或多次seed；H1974的5次61–63ms真实尾仍OPEN。
- 独立失败证据 `docs/evidence/M0/PLAN029-H1995-H1993-REAL-NORMAL-1M-POSTBUSINESS-PARSER-FAIL-20261116.json`记录原SOURCE34e870；cursor的正式`evidence_refs`仍保留旧源8ed70对应H1992已验证真实Normal，不交叉虚报。当前H1995新SOURCE联网结果尚NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1995 source-lock H1993 real original native FAIL at only the new application download checkpoint parser (Stop NOT_RUN), repair genuine bounded recv crossing and rerun exactly one normal 1MiB mixed P2; no product semantics or performance gain promotion."}
```
