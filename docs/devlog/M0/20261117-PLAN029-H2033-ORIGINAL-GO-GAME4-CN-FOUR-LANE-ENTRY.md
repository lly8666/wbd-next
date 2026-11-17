# PLAN029 H2033｜首个真实 Game4 CN 拒绝发生于原 Go CLI assembly

- 收齐 H2030 [原生Action43900614704](https://github.com/lly8666/wbd-next/actions/runs/43900614704)：cheap/Go/Rust编译PASS、Game4真实场景进入Windows客户端启动，但原日志明确`PLAN029 CN split Game2/4 is not yet wired; select Normal (one lane)`、进程退出，Wintun/真实两出口业务及双Stop **NOT_RUN**。原失败独立保留，不诊断为Rust GameAdapter失败。
- 精确定位在单Go assembly `manifest-plan020-m0.json` 对原 `cmd/wbd-client/main_windows.go` 的旧`if *splitEnable && *lanes!=1`检查，发生在进入已接线的`runM0NativeV4WindowsGame`前。当前`r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go`只拒Game2，而生成的Go入口仍误拒Game4。
- 仅改为`split-enable`允许`lanes==1||lanes==4`，2 lane/异常lane继续拒绝，原CN规则文件绝对路径、OS WAL、四TLS lane、Defender精确Allow及Rust单Wintun不变。同步更新的完整生成`main_windows.go` Git blob `4ca2c5625e59987bf3659e4dc9a18227604a530d`是唯一manifest`result_blob`，不绕过`prepare_windows_wiring --check-only`。
- H2031 [Action43901130216](https://github.com/lly8666/wbd-next/actions/runs/43901130216) 独立Normal Tunnel 20..30条/2..3s来源真实Npcap/WSL2 eth0密文抓包与业务/双Stop **PASS_SCOPED**；但单靠物理加密抓包不能逐record解密证明具体padding字节，条数/时间由Rust组件单测证明。这份证据不是Game4合格证据。
- 本H2033真Game4四lane Windows/WSL2 DNS FakeIP、物理Direct TCP/UDP、Tunnel TCP/UDP、owned Stop **NOT_RUN**直到原签名场景交付。共享CDN同IP反例NOT_REQUIRED，028/030不动。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2033 permit already-wired Game4 four lanes through generated original Go CLI while retaining Game2 fail-closed; synchronize manifest full blob, actual Game4 native evidence pending."}
```
