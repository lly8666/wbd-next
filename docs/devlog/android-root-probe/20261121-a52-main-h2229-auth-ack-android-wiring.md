# A52｜将main H2229认证累计ACK接进真实Android Original RAW M4

## 原因与代码路径

main已经合入H2229 Linux/Windows累计ACK与10ms纯ACK共用规则；A51之后Android虽用main `parse_data_packet_fast` 和65535外层窗口，仍把真实RAW接收的 `android_seq_anchor=max(absolute+wire_len)` 直接当出站ACK，不具有累计无洞语义，且无M4纯ACK回送。移动网络乱序时会提前确认未收齐的外层序号，只有下行时又可能迟迟不给对端TCP-looking ACK。此处修真正原M4数据面，而非UI假开关。

- 直接复用main `v4_presentation_ack::NativePresentationAck` 与 `presentation_ack_only_due`，初值是原Go授权过的handoff `rx_boundary`。Android RAW严格候选先进入原M3 AEAD+unique PN/replay；只有原M3已认证的记录调用 `verified(seq,len)`，只有前向连续头推进才可能触发纯ACK。原高水位 `android_seq_anchor` 仍仅服务M1 seq32延伸，不能再作为ACK。
- TX纯ACK走现有Bionic `AndroidBoundRawTx.send_built_outer` 与共享 `ipv4_tcp::build_presentation_ack`，精确同代原tuple、原物理Network/ifindex/MTU、受BorrowFence和owned Stop控制；无新UDP/Go/JNI逐包发送、无重封/复制PN、无外观之外的认证反馈。纯ACK需要发送端SEQ，初值来自原Go protected Detach，后续只在原Rust FrozenRecord确切 `sendto` 成功后更新至该copy的末尾，不能ACK尚未复制的M1排队序号。
- 原RX worker只在出现新待确认累计头时用原eventfd发一个唤醒，原TX worker同一线程发送并用main 10ms时钟合并；eventfd经poll后消费，Stop退出仍以同代shutdown+join为权威，无事件自旋、无新的线程与长期短轮询。已有纯ACK不当作Health/M2或真正业务交付。
- 增加H2229纯Rust原账本的Android wrap/乱序/10ms负例，Linux原Oracle使用 `rustc +1.85.1 --test` 直接执行main源文件；签名APK源码门检查确切主线账本/真实RAW构造及Stop；生产ARM64/x86交叉构建与原Linux server oracle继续通过同SOURCE的原Workflow检查。

## 范围与未证明

本轮只完成Normal/off外层控制报文接线。主线最新 `31ce49d9` 已由A51真实双父合并；A51最后 `f285cc79` 的原Go/Rust双ABI、签名APK、Linux Oracle、M3和DNS Host 11 SUCCESS/4 SKIPPED。旧A48用户真机的原M3 DATA双向收据属于旧SOURCE，不能转写为A52真实下载/RTT/CPU或Android固定FEC/Game。仍须用户自愿用真实手机对照相同网络/端点完成TCP上下载、无上行时下行ACK、乱序、Stop并确认对应A52同SHA。不自动部署任何实体手机或服务器。

## 后续真正全功能接线

此处形成与main一致的共同接收控制基础。Root App仍硬编码normal；原Go Android冷入口阻断Fixed/Auto/Game，原Rust Android M4仍无这些模式对应的原生产FEC/Game owner，Android CN System Resolver/TCP53全链也未连通。本轮不假开关、不冒充全模式完成。后续在M4唯一owner架构中按原FEC2/Auto、Game2/4、DNS/规则分流逐路径打通并单独真实资格验收。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"复用main H2229原Rust已认证累计ACK和10ms纯ACK门，将Android Normal/off真正RAW RX→M3→原TX worker→IPv4/TCP ACK-only接线，新增同源Rust语义测试与原Bionic/Stop源码门；真机性能与高级模式仍待验。"}
```
