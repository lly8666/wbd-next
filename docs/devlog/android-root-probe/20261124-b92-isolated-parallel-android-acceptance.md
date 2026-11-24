# B92｜隔离并行 Android 原生验收

B91 SOURCE `2b6b904b874065dd7a03f1152ed836662e606e05` [Action 45412992618](https://github.com/lly8666/wbd-next/actions/runs/45412992618) 11 SUCCESS/1 FAILURE/5 SKIPPED；[guest 138514706320](https://github.com/lly8666/wbd-next/actions/runs/45412992618/job/138514706320) 真 KSU 部署及物理 Bionic UDP DNS + TC→同 Network TCP PASS；系统 DNS ip link add alias/type dummy Android parser FAIL，清理读回 NOT_PROVEN，余12项 NOT_RUN；[artifact 14931410962](https://github.com/lly8666/wbd-next/actions/runs/45412992618/artifacts/14931410962)。正式 APK/双 ABI/Host 仍 PASS。

B92 修正系统 DNS 原 cold owner 的 ip dummy 创建/alias 设置顺序，不动热路径、权限、路由/认证/Stop 契约；Host fake kernel 回归同步。专项分7个互不共享内核的 KSU guest（UID、Normal、Game2、Game4、物理/隧道/CN 系统 DNS），fail-fast false、max-parallel 7；共同同源 native+CN artifacts，不等 Linux server，不重复物理 bootstrap 与 B89 七模式 preauth。各 shard 内按原 Stop 清理串行；独立 root 命令读回并记录 baseline 与失败输出。另一个真实 RootService lifecycle guest 用原 D2 同源 server 夹具，前后台/明确 Stop/模式重启/真实 WiFi loss 与恢复后手动 START；仅 preauth，完整 READY 后自动恢复及 profile cold switch 仍 NOT_PROVEN。测试外层1460。B92 待运行。无 benchmark、无额外产品防御、无 main/真实手机/外部服务器操作。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B91 Android scoped DNS evidence; repair actual Android dummy interface command, isolate seven specialty shards and run real preauth RootService lifecycle separately."}
```
