# PLAN027 H457｜从H456真实红项恢复并启动A2/A3

H456 `ea098890` 新增source-locked A2/A3场景，但 `.github/workflows/m0-plan027-a2-a3-fanout.yml` 的 heredoc Python 左边无 YAML 缩进；run40994656424 无jobs、governance40994657501 / maint40994657529 / Win preflight40994657611全部ScannerError。原H455 Normal结果已在 dispatcher 文件创建前完成，因此不可能回溯 workflow_run。H457只修 YAML 并以明确 `[plan027-a2-launch]` 一次性push触发，冻结PRODUCT_SHA=88ba0900及原run40993452459，验证两边原构建产物/hash及产品源码未变后，按3个独立Actions派Normal10M/250ms 0%、Normal30%和Fixed最高30%；先前没有这些场景的成功或派发。

H455 B fanout Action40994430848真正派了6个：Fixed `40994441580` 的Windows/Linux真实UDP25/25、TCP echo、owned Stop都PASS，但测试仍强制旧M2 MATURE_SCOPED而将整Action判FAIL。Auto `40994443303` 是真正业务失败，Windows源发送385收0、Linux发送100收27，双端Ready但Windows方向零送达和Stop不能称PASS。Game四种scoped Actions40994446899/48846/51624/53410均success，尚须单场景证据复核；不重派任何已通过场景。

outer-repair-v3计量校验原有30% loss强制`R/offered>=6%`，与PLAN027明确“6–10%仅参考、不得无损凑重传”冲突；删除硬下限，新增zero-R真实零repair_packets一致性，R<=.10F及真实两OS tc损伤、业务、Stop硬约束保留。原标记`R/C`实际是R/offered目标字节，改单列`R/offered_target`并明确`R/(F+R+C)`。对应正/负例同步更新。功能未变，此批未验证Actions PASS。

PLAN027①源码候选，②A2/A3现在实派待结果，③B Fixed/Auto两红原始证据及后续生命周期待修，④C/5min未测，⑤继续按SOURCE真实性判定。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix Actions YAML/immutable one-shot scenario control and false repair ratio gates, preserve product source and all real failures."}
```
