# PLAN028 M0 H1606｜WSL内核实网环境外因：根镜像源DNS失败，精准镜像回退

H1605 SOURCE`cee5ced946d4111fd69fe51e6f03fb949edaf550` Windows+Linux H1602原生 Action [43040746444](https://github.com/lly8666/wbd-next/actions/runs/43040746444) 整体 **FAIL**；原始 Job`130593544114` 在 `Real WSL2 Ubuntu kernel boot and TUN prerequisite` 阶段退出，错误精确为 `Invoke-WebRequest ... releases.ubuntu.com ... No such host is known`。此时Linux产品构件复用已经打印`H1605_LINUX_SOURCE_QUALIFIED_SAME_BINARY_ISAL_SHA256_PASS`，Windows正式原Go EXE+Rust DLL旧SOURCE零产品diff及本体hash检查`WL_V2_REUSED_WINDOWS_NATIVE_EXACT_BINARY_SHA_PASS`，真实Npcap1.88安装成功、WSL尚未import且没有业务Socket/inner MTU测量。尾部`WBD_NPCAP_DRIVER_CI_CLEANUP_PASS`，无Wintun产品Stop应宣称。**分类为 ENVIRONMENT_BLOCKED_PRE_NATIVE，H1602业务 NOT_RUN**；同源治理`43040746448`、governance-maintenance`43040746447` 均SUCCESS，原失败Action保留。

H1606针对这个唯一外部下载点（当前原 `releases.ubuntu.com`）添加一次**官方Ubuntu镜像地址备选** `mirror.cpsc.ucalgary.ca/mirror/ubuntu.com/releases/24.04.5/ubuntu-24.04.5-wsl-amd64.wsl`。主源正常则完全不触发；备用只当`WBD_PLAN028_WIN_NEAR_MTU_SMOKE=1`且主源下载失败时尝试一次。备用仍需通过既有精确原Canonical Ubuntu SHA256 `bb415d824822c4b878125729af451a5d18fb13d1cf5cbed9a7393ad64ac6039e`，否则绝不import/运行。没有使用任意镜像、修改WSL内核、放宽签名或业务硬门，测试仅一Windows Wintun+四Linux，原产品二进制依旧复用、所有hash/后端来源另存。

本提交启动一个H1602真实近MTU短场，失败则以明确第一步环境/产品界限落账，**不继续盲目换镜像重派同族**。此前3次Ubuntu apt DNSFAIL也保留，H1601同账号五客户端150s仍PASS_SCOPED，与本SOURCE无混淆。用户的双Wintun排除不变。

```feature-impact
{"kind":"none","reason":"Scoped H1602 CI Ubuntu WSL official mirror fallback with exactly pinned SHA after host DNS failure. No Go/Rust product, default or new interface changed."}
```
