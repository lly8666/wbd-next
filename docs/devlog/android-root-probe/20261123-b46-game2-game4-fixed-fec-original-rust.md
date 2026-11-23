# B46｜Android Root原Game2/4 fixed Game FEC：Go TLS→单Rust GameAdapter→多RAW/TUN

## 已知基线及关键修复
B45b `9f7685bd25a7cbc6fdd67e81555b6dd600bb4188` [Dual64 #45138246728](https://github.com/lly8666/wbd-next/actions/runs/45138246728) **completed SUCCESS：11 SUCCESS/4 SKIPPED**，[治理 #45138246623](https://github.com/lly8666/wbd-next/actions/runs/45138246623) SUCCESS。B45是软件BUILD/HOST资格，Game4真实实体仍NOT_RUN。B46代码审核发现B45的Android Rust `m4_start`虽然验证 `android_lanes.len() 2|4`，却把底层 `android_raw`过滤写死 `v.len()==2`，使真实Game4无法安装M4；本批按同组2|4实际RAW数修复并加真实源码门。**B45软件PASS不代表此Bug已被设备测到。**

## B46一批业务功能
1. 在Root正式App保留原Normal/Fixed/Auto、Game2/4-off并新增 `game2-fixed` / `game4-fixed`，原档位Spinner选择0..6，三种App UDP/53选择、所选普通UID路由、Health设置、配置预设和原 CA/证书入口都走已有Root Activity→Service→`OriginalGoCommandArgs`。新GUI名称只映射到原Go产品命令 `--mode game2|game4 --game-fec fixedN`，绝不发明第五/第六种线协议。
2. 原Go Android仍为真正选定物理Network的2/4 FakeTCP SYN→每条独立原标准TLS/身份证书/密码/lease/同epoch，要求每条实际 `session.verifiedGameFec` 与要求的 `N+1` 相符。由同一原GameAdapter/Rust group join之后，新增私有M4启动参数 255=off、0..6=fixed。任何回包/身份不一致不得从App flag自封为FEC ready。
3. 原Rust `AndroidGameWorkers::start` 在启动现有1TUN +2/4RAW M4之前，直接调用原 `GameAdapter.enable_game_fec(profile,false)`；无新加密、FEC wire、replay owner、Go/Java逐包。单TUN TX继续 `offer/drain`，在现有 eventfd 循环用原 `poll_game_fec` (4 bounded quanta) 和 `game_fec_next_due_ns` 发送寂静时到期的校验符号，与原Game4 0/4/50/140ms copy stagger 同RAW发送器。
4. 每个已有原M3 RX lane先经原 `GameLaneOpener.open` 完整AEAD/PN/唯一性，再将已验证Game id/payload交同一个原Linux FEC `GameReceiveOwner.prepare_opened_fec_batch`；原共享恢复器一次最多16个IP帧，先全部校验原租约与原DNS/53反向映射，**直接改写FEC-owned Vec帧而非另copy一批**，再由唯一原TUN原子式多帧提交/ `finish_fec_batch`。若部分内核写成功则停止原worker并拒绝虚假完整交付；没有独立DNS/TUN/FEC Worker。Game-off RX原路径完全保留。
5. 在已有Linux原Rust `wbd_fec_network_game_group_counters` ABI 上开放Android只读16计数，原Go 1Hz status ticker读取实际source/parity/内核已复制/recovered候选/expired/failed，原 `RootFecStateBrief` 正式纯Java解析器展示；**recovered candidate不能替代同一M4真正TunDelivered，更不是用户App E2E**。
6. 更新原App参数+档位/预设、原状态纯JVM用例、B40/B45实生产源码门，新增B46跨层源门。保持唯一Draft PR#36、主线/M0隔离，不跑未经授权的Android/Server实体测试或重复旧x86 KSU/TAP探针。

## 验收边界
这一份是B46新SOURCE施工日志，只有自动Android Dual64对**本SOURCE**编译原Go/Rust ARM64+x86_64、签名Root APK/Java Host、原Linux Normal/off Oracle/原M3 DNS Host以及Feature catalog全成功才能记 `BUILD_PASS/HOST_PASS`。真Android Game2/4 fixed Game FEC完整TLS/实际多帧恢复/三DNS/UID/Stop及CPU/吞吐仍 **NOT_RUN**；旧B45b软件通过也不能继承实机资格。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B46修Game4真实4RAW启动阻断，Game2/4固定Game FEC0–6沿原TLS保护模式与原Rust GameAdapter TX/RX/Health/Stop、正式App参数/预设及原Linux FEC状态回读。"}
```

## B46a｜同源首轮Go编译与Rust目标环境修复

B46原产品SOURCE `c3fe6df56f0cc87070c6e9bea182af5d69efd2be` [Dual64 #45143767720](https://github.com/lly8666/wbd-next/actions/runs/45143767720) **completed/FAIL**，精确6个DNS/CN/M3 Host Job SUCCESS，arm64-native FAIL；签名App/Linux Oracle跳过。Rust AArch64与x86_64原生代码都已经release编译完成，Go失败 `V4ClientSession.verifiedGameFec undefined`：字段只在原 `V4ServerSession`，原客户端 `EstablishClientV4`早已在受保护reply之后精确校验 `extension.GameFec!=opt.GameFec`。B46a删除不必要的二次字段访问，不新增Go假确认，并把源码门改为校验原 TLS 真正已有的受保护回复核验。第二问题是Rust `target_env="android"`非有效target_env；原Android NDK目标由 `target_os="android"` 标识，本次把原Linux FEC计数 ABI 的编译门改为原Linux三元组或Android AArch64/x86_64，避免Android端缺 `wbd_fec_network_game_group_counters` 实际导出。保留旧失败，B46a必须本SOURCE新CI成功才记签名App/BULD，实体FEC仍NOT_RUN。

## B46a同源软件资格收口（实机未验证）

最终产品SOURCE `3952345601d3bd77e9f8c6f5bc4c0938a6b9b438`：[Android Dual64 #45144428626](https://github.com/lly8666/wbd-next/actions/runs/45144428626) **completed/success，11 SUCCESS / 4 SKIPPED**：Android Go/Rust ARM64+x86_64双ABI、签名ARM64 Root APK与原App三DNS/Game2/4 fixed0..6 argv/预设/状态纯JVM门、Linux原Normal/off Server Oracle、Linux x86 D2-S0、六个DNS/CN/M3 Host Job均SUCCESS；ARM64 Cuttlefish host-admission仅为宿主准入，**不是**Android guest运行；四个x86 KSU/NativeBridge/D2-S1/TAP guest SKIPPED。 [Feature catalog #45144428602](https://github.com/lly8666/wbd-next/actions/runs/45144428602) SUCCESS、Governance SKIPPED。之前首轮B46 `c3fe6df56f0c` 构建失败保留在历史。

结论严格限定 **BUILD_PASS/HOST_PASS**；未执行实体Android或个人Linux Server部署，Game2/4 fixed 原真实双向TCP/UDP、实际FEC恢复到App、DNS、UID路由、owned Stop、CPU/吞吐皆 **NOT_RUN/NOT_PROVEN**。原 Go 客户端 `EstablishClientV4` 已直接校验受保护回包 `extension.GameFec==opt.GameFec`，不是不存在的 `V4ClientSession.verifiedGameFec` 二次检查。后续首先以真机普通业务验证为准，不转向极端工况/新安全加固；本轮不运行设备。
