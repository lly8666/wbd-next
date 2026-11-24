# A34｜API36真原FakeTCP已建立，TLS 14,997ms 后 OTHER

用户自主运行A33 SOURCE `f8031ef1cf2f15e2769208d76bf2b072275b6084` 的API36安全TXT（33事件）：`ORIGINAL_GO_ASSOC_ESTABLISHED`→`ORIGINAL_GO_COLD_PRODUCT_PREPARED`→`ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED`，14,997ms后 `ORIGINAL_GO_TLS_HANDSHAKE_FAILED_OTHER`、exit1；Go/TUN/RAW/SYN ACK等历史阶段保持。原Linux server RAW接包/SYNACK来源及ClientHello抵达、TLS验证/认证/32租约、Rust M4 TCP UDP和认证后owned Stop全部NOT_PROVEN。15s接近候选绝对预算，但OTHER不是确证Timeout。

A34在原ClientAssociation emitter成功调用原raw.WriteSegment之后，首次非空bootstrap Payload只记固定`TX_OK`；在原AF_PACKET真ReadSegment+原4元组`MatchesInbound`后，只记首次`RAW_PEER_PAYLOAD_RX`；返回失败时按本会话实际状态记未观察方向以及原已有重传是否发生。都不记录原payload/账号/IP/Key/证书/错误原文，不增加TLS前导、额外socket/发送器、强行重试或改变TCP/AEAD/Stop。原TLS错误分类只对确切`faketcp.ErrBootstrapTimeout`、OS deadline、context cancelled、bootstrap closed等固定类型追加分支；未分类OTHER且原15s预算确已耗尽时为`DEADLINE_ELAPSED_OTHER`（仅观测时钟）。Java原Service将原Go固定Marker转脱敏安全TXT，CI签名APK、双ABI、真实Linux Oracle、Go及Java Host正反例独立验证，禁止因绿色冒称手机或服务器PASS。

下一步唯一真实外部门：用户自行使用新SOURCE签名ARM64 APK导出一次固定TXT；若有原Bootstrap payload TX而原RAW对端RX未见，先查原服务端AF_PACKET ClientHello接收及传输回程，而非改TLS/证书/默认全App路由。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A34基于真实API36原FakeTCP Established后TLS 15s OTHER，对原Bootstrap收发及TLS实际截止时间作无敏感分层诊断，原协议不变。"}
```

## A34a 同源真实CI失败及最小语法修复

SOURCE `a64f68f03467a1407629067b27c6ee02f802ef5b` [Android dual64 Action #44697153076](https://github.com/lly8666/wbd-next/actions/runs/44697153076)：原 ARM64 Go/Rust、A34 Java安全收据、签名APK、Linux x86 D2-S0、前置Host均SUCCESS；`linux-original-server-normal-off` 在刚新增的 Go分类测试shell `-run` 命令单引号截断时报 `unexpected EOF while looking for matching '\''`，**Linux真实oracle未执行，绝不可将其当产品协议 FAIL 或标全绿**。旧 FAIL 保存。

本次仅替换整个损坏的固定Go测试与原build循环，保留原测试正则/Go标准TLS/原所有协议；用一行完整shell命令避免JS替换时 `$'` 被解释；并在便宜的 `root-arm64-app` Host前置检查对 `linux-original-oracle.sh` 执行 `bash -n`，防止以后编译后才发现类似错误。保持同SOURCE已构建过的APK产物不被本批充当新SOURCE产物，需重新完整执行新SOURCE Oracle和签名APK门。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A34实测发现新增Linux原Go分类单元测试的shell插入引号损坏；仅修测试命令及前置bash -n，保留首次红CI收据。"}
```

## A34b 恢复原已验证Oracle为唯一基线

A34a SOURCE `1658573124a5f91e8ba400422208d2f85dfe432b` [Action #44697865675](https://github.com/lly8666/wbd-next/actions/runs/44697865675) 的新 `bash -n` 正确拒绝Oracle文件末端遗留的重复Go/Python块（第157行）。ARM64原Go/Rust、其他Host已验证范围保持；root-arm64-app在Host便宜门 FAIL，Linux原Oracle不具业务资格。**不将历史失败写成成功**。

本次彻底舍弃污染后的脚本，以历史完整真实通过的 `b629c850f17670a9a28fdf6e7a2f13660ed81990` 版本为原件（156行含结尾空行、4对Python heredoc、唯一Go编译循环），只在该 `go build` 循环之前插入3行源锁Go错误分类测试。预检确认更新后159行、原四段Python不重复、唯一Go build和新测试且尾部完整；原测试oracle全部保留。新SOURCE需前置bash -n、真Linux Oracle和签名APK全成功后才交给用户验证。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A34b清理历史patch污染的Linux Oracle残尾，直接恢复已通过完整脚本并仅接入一次原Go固定分类测试。"}
```

## A34c 纠正 Go 分类测试标签（保留首次真实编译失败）

源锁 `b45df05805eb54b9c20059baa21365299c2d8793` 的 [Action #44698536941](https://github.com/lly8666/wbd-next/actions/runs/44698536941)：10 SUCCESS、4 SKIPPED、1 FAIL（`linux-original-server-normal-off`）。原Go/Rust ARM64、签名APK、Java Host、Linux D2-S0及其他Host成功。Linux Oracle修复的完整shell已通过 `bash -n`，但新增 `go test -tags wbd_v4_embedded_go,wbd_v4_fec2_product` 编译时，历史`bridge_v4_embedded_linux_test.go`引用只在`wbd_v4_native_probe`标签下定义的`v4RawCheckSum`/`v4RawC2STestPacket`，在测试执行前FAIL。**不补假的helper、不改变原生产代码或原Linux真实Oracle**。A34固定分类仅依赖公共Go `admission_v4.go`/标准包/原 `faketcp`，故本次将该独立Go unit test改为默认无嵌入标签执行，避免牵连不匹配的Linux native probe测试编译；原有带标签的Linux client/server `go build`、netns真实TLS/租约/M4/wire验收仍保留并后置。新SOURCE必须分别记录Go单元测试与真实Linux oracle结果。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A34c实测历史embedded_go测试标签会缺少native_probe helper，仅将独立Go分类测试恢复公共无标签入口，Linux真实产品构建/协议不改。"}
```

## A34d 终局同源验收锁定

产品SOURCE `c010f7357d0334c48c479012011b6cdb7dad1e4f` 的 [Android dual64 Action #44699225975](https://github.com/lly8666/wbd-next/actions/runs/44699225975) **completed SUCCESS：11 SUCCESS / 4 SKIPPED / 0 FAIL**。`arm64-native` 双Bionic ABI原Go/Rust与ARM64 16KiB门、`root-arm64-app` signed APK及Java safe TXT负例、`linux-x86-original-server-d2-s0`、`linux-original-server-normal-off` 原Linux Go/Rust真实TLS/自动32租约/UDP M4/Stop/wire Oracle，连同M3/DNS Host门均成功；后者真实日志：`ANDROID_A34_ORIGINAL_GO_TLS_CLASSIFIER_HOST_PASS`、`ANDROID_A3_LINUX_SERVER_ORACLE_PASS_ANDROID_RUNTIME_NOT_RUN`。四个SKIPPED：x86 KSU Native、NativeBridge、D2-S1、TAP guest；ARM64 Cuttlefish仅host admission SUCCESS，不代表guest。

[源锁签名ARM64 APK工件 #14611433699](https://github.com/lly8666/wbd-next/actions/runs/44699225975/artifacts/14611433699)，[Linux原Oracle工件 #14612830235](https://github.com/lly8666/wbd-next/actions/runs/44699225975/artifacts/14612830235)。原始手机 **仍仅为A33 SOURCE `f8031ef1`** 已证FakeTCP Established→TLS Attempted→14,997ms OTHER；A34新功能的真实手机TX/RX/timeout类别、服务端原RAW来源、TLS认证/32租约/原Rust M4双向App TCP UDP/内核UID与joined Stop均 **NOT_RUN/NOT_PROVEN**，不因Host oracle PASS升级。历史A34 `a64f68f`、A34a `1658573`、A34b `b45df05` 产品Action的脚本/测试标签FAIL均保留原结论；本资料提交不重新构建新的APK SOURCE。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A34完成同源构建和原Go TLS错误分类/LINUX Oracle 11 SUCCESS 4 SKIPPED收据，保持Android真业务NOT_PROVEN。"}
```
