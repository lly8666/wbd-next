# B49｜前台明确发起的原生一键冷Network重建

上批B48产品SOURCE `8b5d4ec18ace6c97300f01f8d96605834e5e1f67`，[Android Dual64 #45163517303](https://github.com/lly8666/wbd-next/actions/runs/45163517303) 完成 11 SUCCESS/4 SKIPPED，原Go/Rust Game2/4真实组Stop与UID/RAW/RST清理已有软件接线，真机Game未验。

本批不是新的网络或包代理：正式Activity选择当前ConnectivityManager列出的目标实体Network，用户主动触发一次操作，经既有Service `STOP`。只在B48真正 `previousOwnerStopConfirmed`（原生M4已join、安装过的UID路由已撤、Game组Stop与进程EXIT0）且旧owner完全退出、无并发START后，使用**已有前台每秒状态刷新**重新枚举并精确匹配用户选中的 handle/ifindex/IPv4/MTU，仅调用现有 `start()` 一次；之后原Root App仍重复执行当前包名UID与网络核验、凭据私有写入、原Go FakeTCP/TLS/Admission/租约、原Rust唯一M4、私有UID route。旧Stop未证、目标已变化、离开前台或手动Stop立即取消意图，不自动复活旧session。

新 `RootColdNetworkSwitch` 是纯Java一次性UI决策（不缓存权限/Secret），独立Host测试覆盖Network身份、失败Stop、丢目标、一次性和离开取消；官方Root APK源码门执行。Go/Rust生产TLS、M3/PN、DATA与Stop完全复用，新增0个数据线程/定时器/热路径操作。不是无人值守onLost自动重启、无缝迁移、跨设备恢复或实机业务PASS。本SOURCE双ABI/签名APK/Linux oracle只按实际Actions定级；实体Network冷切换、TCP/UDP/DNS和CPU/吞吐仍NOT_RUN。只改实验分支，不动main/M0与实体设备。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B49前台一次用户动作接原B48 Go/Rust owned Stop→精确Network重选→原Activity START，不增加后台Root启动或数据面；真实纯Java门及签名APK同SOURCE核验。"}
```

## B49a｜功能卡容量修复

B49 SOURCE `344594efcf893bfae93f737ae4c62fa9a1956e47` 的 [Feature catalog #45168583926](https://github.com/lly8666/wbd-next/actions/runs/45168583926) FAIL：当前摘要/GUI超16KiB；本次只缩文字，保留历史 verification/FAIL，未变动原Go/Rust/App代码与已在途产品Action。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B49a仅将当期卡片摘要/GUI压缩至16KiB以内，不动产品实现或历史验证。"}
```
