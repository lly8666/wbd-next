# A5 2026-11-17 独立Android ARM64原Go/Rust Root应用，不使用VpnService

工作基线 `20d7c7ffaaeefcae96ab5f03c656994466420eac`：原Go完整CGo Android arm64 CLI + 共享Rust M1/M3/M4/Health/Stop/Root UID journal同源码 [Action44033543628](https://github.com/lly8666/wbd-next/actions/runs/44033543628) **PASS**（原M3与纯Go路由事务单测也PASS）；治理[44033543634](https://github.com/lly8666/wbd-next/actions/runs/44033543634)PASS。真实ZIP artifact14305783711解包：Go ELF SHA256 `d39ffe9cf579e8b19a1bebbfa6f912c7ff08fed54084ab8dabc6b8273699dcb7`，Rust ELF SHA256 `6a3b1b808e382db53272f46326fee21f461660a97fe3cbb0ea03f3562b95035f`，ELF64 machine183/16KiB均真。仅Android arm64-v8a；PR#36 Draft，main/M0不动。

## A5具体新增真App入口

- 独立包`org.wbdnext.rootclient`，独立目录`android/root-app`；**自己的Manifest没有VpnService/BIND_VPN_SERVICE**，历史`android/app` VPN壳不改且不属于Root产品。Java层没有TLS/AEAD/PN/packet-callback、JNI伪装、FakeIP或全局VPN路由。
- Activity列举**真实`ConnectivityManager.allNetworks`**中物理Wi-Fi/蜂窝/非VPN Network，读取`Network.getNetworkHandle`及`LinkProperties`IPv4，核对Java`NetworkInterface` ifindex/MTU/UP及本机IP；用户仅选择一个Network、字面服务器IPv4、标准TLS/SNI、原WBD用户名/密码、32B离线route key、可选CA PEM和普通单App UID。网络消失/变化时前台Service请求Root Stop，且原Rust仍独立物理scope判定。
- 密码和route key写入应用私有0600普通文件及fsync，命令行只传**文件路径**供原Go`O_NOFOLLOW`读取，绝不将明文放到argv/Intent/日志，Go进程退出后删临时凭据。Java从APK`assets/native-arm64`用8KiB流校验Go客户端与原Rust共享`.so`的SHA256和完全相同SOURCE，不分配多份11MiB ELF缓冲。
- Root `su -c`命令将已核准真实ELF复制到`/data/local/tmp/wbd-next-root` 0700目录（Android10+不能直接执行App可写data），启动前检测旧root`owner.pid` + `/proc/$pid/stat`起始时间并拒绝仍活的原Owner，绝不在他还运行时替换旧binary。随后`exec`真实原Go arm64 ELF，`LD_LIBRARY_PATH`指向同源Rust`.so`；不自行实施密码认证/内核数据循环。
- Stop只向持有Root文件中**精确PID+内核起始时间+`/proc/$pid/exe`真实二进制**的原Go进程SIGTERM，原Go沿原`signal.NotifyContext`撤单UID路由journal和原Rust M4 Stop/join；前台Service只在原进程确实退出后显示结束，发送信号不冒充Stop完成。Native就绪必须原Go`V4_ORIGINAL_GO_CLIENT_NATIVE_READY`与`V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED`两个真实日志收据全部出现，且仍标流量**未实测**。
- CI新增`root-arm64-app`依赖同一SOURCE的原生ARM64 job，用GitHub Actions当前Run Artifact验Go/Rust ELF机器183、PT_LOAD >=16KiB、SHA及SOURCE；AOSP `javac`/`d8`/`aapt2`/`zipalign`/`apksigner`构建原生Java SDK35签名Debug APK（临时CI密钥绝不上传）；再解包验证APK内Go+Rust实际文件、同源码哈希及无VpnService Manifest。与另一个原M3 wire oracle并行，所有门独立PASS才算App构建成功。

**A5源码尚未运行本次CI**；手机Android16 KSU安装/Root授权、原Go真实TLS/证书/lease、真实系统`ip -4 rule uidrange`、TUN IPv4链路、双向TCP/UDP、Jumbo、切网/Stop、DNS/热点/性能/功耗严格**NOT_RUN**。成功构建APP也不能假称已可稳定联网或性能已测。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"独立Android ARM64 Java原生Root App，真ConnectivityManager物理Network、私有凭据/单UID、同SOURCE签名APK内原Go/Rust ELF与严格PID/starttime Stop，不新增VPN/JNI/TLS/AEAD；SDK/真机单独门。"}
```

## A5原Go/Rust同源Root APK三门PASS及后续Root目录安全补丁

- SOURCE 1cfbfe2a91bc369037f9f78abf88cf76320900dd: [ARM64 Action44035287415](https://github.com/lly8666/wbd-next/actions/runs/44035287415) 原M3 wire oracle、真实原Go/Rust Native ARM64完整CGo、独立Java SDK35无VpnService Root APK三个job **全部PASS**；[Governance44035287468](https://github.com/lly8666/wbd-next/actions/runs/44035287468) PASS。A5 APK artifact14306977329真实解包：ZIP SHA256 7b8da07169db2e0565b4cdeb47f64e6c1389de59da42e09ac1deca587a8fd33f，APK SHA256 4faad321629e88435a70e495315e8177e45bba614e73f424c5d1d5a3faf386a7。APK内原Go ELF SHA256 d39ffe9cf579e8b19a1bebbfa6f912c7ff08fed54084ab8dabc6b8273699dcb7，原Rust共享so SHA256 6a3b1b808e382db53272f46326fee21f461660a97fe3cbb0ea03f3562b95035f；双方machine183，最小PT_LOAD 16384，APK原生来源=1cfb，Manifest无VpnService，无Android x86资产。
- 本后续安全加固：/data/local/tmp是可触及父目录，Root启动脚本旧版先mkdir -p/chmod，可能沿预建symlink修改其他目录权限。现在**任何chmod、ELF复制之前**禁止symbolic link，只有缺失时创建0700目录，之后使用真实stat核对owner uid0/mode700，外国目录失败且不修改。启动前先核原活PID/进程starttime再覆盖ELF，保留原进程精确Stop能力。此修复SOURCE须重新跑完整CI，旧A5成功不能代替修复版的验收。
- 用户Android16 ARM64 KSU Root授权、真实iproute2 uidrange、原Go标准TLS/凭据/租约、手机双向TCP/UDP、Stop路由及借用资源、网络变更、DNS、耗电/性能、热点评测**均NOT_RUN**；Debug签名非生产发行签名。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"封存A5同源ARM64 Native+原M3+独立无VpnService APK三CI PASS及真实ZIP/ELF SHA，并对共享父目录Root symlink攻击面增加源锁防护；新源码和真机分别验收。"}
```
