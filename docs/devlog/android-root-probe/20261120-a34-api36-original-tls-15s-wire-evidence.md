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
