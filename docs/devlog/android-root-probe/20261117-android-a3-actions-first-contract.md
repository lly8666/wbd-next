# Android A3：Actions-first 与同源 Linux 服务端 oracle（2026-11-17）

- 用户授权仅Android分支开发及Actions测试。所有软件功能先Actions，实体Android16 ARM64 KSU及热点/USB/功耗最终专项另行授权；main/M0与PR Draft状态不变。
- 入场SOURCE `d7e2e2936b283bf1ad4c02dbcec2e59c92297e61`、原Go donor `a7a82db31fe736ffedee330795a3234d358f1984`。Android Action 44035987188 的原M3 oracle、原Go/Rust ARM64 CGo和APK三Job BUILD_PASS；真Android联网NOT_RUN。
- 此次新增同SOURCE Action Job `linux-original-server-normal-off`，必须先下载并哈希核验Android ARM64原Go/Rust资产，再构建原Linux Go/Rust client/server，跑真实Linux netns标准ClientHello、认证、自动/32租约、Rust M4双向UDP及owned Stop。原pcap只在runner中用于结构审计，不上传。
- 新SOURCE尚未执行，Linux server oracle及Android KSU guest、正式双向TCP/UDP、系统DNS/App、Game/生命周期和实体热点USB均NOT_RUN；后续依据真实Actions日志记PASS/FAIL/ENV_BLOCKED，不预先宣称成功。
- 唯一下一步：观察本SOURCE Actions；Linux oracle有证据后筹备真正ARM64 KSU Actions guest/runner，完成 Android APK↔Linux server A3 真连接；不存在运行环境就ENV_BLOCKED而非提前操作实体手机。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"用户Actions-first全功能再实体终验；新增同SOURCE Linux真服务端原Go/Rust oracle，Android E2E未测。"}
```

## 本SOURCE首次治理失败与定点修复

- SOURCE `7296fa2d9c114202c7e7462b737aff980d157889` [Governance44041088212](https://github.com/lly8666/wbd-next/actions/runs/44041088212) **FAIL**：新增功能卡 JSON 超过 16KiB；未进入第二治理门。此失败不影响既有 Bionic BUILD_PASS，也不能把在途 Linux oracle 写成通过。
- 修复仅删除本次新增的重复验证空条目/限制短句、缩短摘要；验收分级和失败证据仍在现行计划与本 devlog 中。改动不触及产品代码或 main。以修复SOURCE的治理为准。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"修复新增Actions-first摘要导致的feature JSON超16KiB，保留原历史与完整计划。"}
```

## A3首轮 Action 真实失败及装配夹具修复

- SOURCE `7296fa2d9c114202c7e7462b737aff980d157889` [Action44041088298](https://github.com/lly8666/wbd-next/actions/runs/44041088298)：`original-m3-wire-oracle`、`arm64-native`、`root-arm64-app` PASS；新增 `linux-original-server-normal-off` **FAIL**：旧 PLAN020 固定 result_blob 与当前 `r0/go_overlay/internal/v4productcli/linux.go` 不匹配，未运行 Linux 业务。原 PLAN020 历史不重写。
- 定点修复仅换为 Android A1 已验证的 pinned original-Go donor + 现行 overlay 组装流程，独立 A3 装配收据记录同 SOURCE；本次未改原Go/Rust协议代码。下一 SOURCE 的 Linux Go 编译/真实网络结果仍 NOT_RUN，待 Actions。
