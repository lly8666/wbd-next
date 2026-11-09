# PLAN028 H1482｜真源ARM64新代就绪回归：装配SHA钉住后复用原工作包

原 `main` `4ed169b6ad35b58588cffa18350102d7c42d1361` 的 [H1480 Action42623579875](https://github.com/lly8666/wbd-next/actions/runs/42623579875) `build` 立即 `FEC2_ASSEMBLY_REJECTED: overlay result blob mismatch: internal/v4productcli/linux.go`，`scene` SKIPPED，无产品/二端业务/可靠性结果。先前H1480首个 Action42623129084 YAML preparse FAIL（无jobs）也独立留存。这两条都是 `HARNESS_OR_CI_FAILURE` / 场景 `NOT_RUN`，不把条件触发说成PASS或产品FAIL。

根因不是业务：`r0/go_overlay/assembly/manifest-plan020-m0.json` 对 `kind=create` 目标 `internal/v4productcli/linux.go` 仍固定旧结果Git blob `95df7528...`，但已修改真实源 `r0/go_overlay/internal/v4productcli/linux.go` 的当前Git blob是 `3617b125eaf317f50423a84fae220216538b8d9d`。装配器先校验**全部 111个操作**再写donor文件，所以正确拒绝变动。仅更新该项`result_blob`到对应真实已写Go源码的Git SHA1；其余本轮修改的 `bridge_v4_embedded_linux.go`、`bridge_v4_linux_server_product.go` 不在这份早期111项清单内，仍由工作流的原Go覆盖源一致性检查复制，不能虚构manifest条目。显式确认二者当前Git blob分别 `dacdde988...` / `c1a3d25...`；原源/密钥/record/正常MTU和所有数据面逻辑未修改。

修复同commit轻量更新H1480工作流注释，以受控`on.push.paths`触发这**唯一实际H1480任务**，不用手工重复dispatch或回头重测original SOURCE66fb。待收新的真正ARM64 Go+Rust build、L0 unit、产物manifest/hash、真180s×五客户端、客户端B冷Health真触发、服务端A延后退休与所有Stop以及UDP无缺失；业务FAIL/未触发都不准记修复PASS。保持H1478原Alice10欠包、Windows原1800 NOT_QUALIFIED、H998热MTU和Android/物理NOT_RUN原样；PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Only repin exact overlay assembly hash for the already-changed Go source and re-run one previously blocked native validation workflow."}
```
