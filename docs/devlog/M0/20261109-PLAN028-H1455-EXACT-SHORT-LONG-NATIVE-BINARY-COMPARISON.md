# PLAN028 H1455｜短PASS、长CI FAIL、当前600s三路源的原生机器码核查

从真实SOURCEe6aa短测Action42502567549、SOURCE724a长测Action42546907707、SOURCE548a现有600s Action42555320138原始artifact取出Windows bin manifest、完整DLL和EXE；从短测report、长测/当前Linux产品包取原生Rust .so与原始Go两进程。Windows原始Go客户端EXE三个SOURCE的SHA256均 `f0c34f379bf6ff6ca265764ea84e7a1a1cc27513984a5631cd4d4acfe5f5b363`；Linux原始Go Client、Server、Rust .so三个SOURCE的SHA均逐字节一致。GitHub提交比较e6aa→724a（26 commits）与724a→548a（7 commits）产品Go/Rust源文件改动均0。

Windows Rust DLL的完整SHA不同，但三个DLL同为2453504字节；PE .text可执行代码段1669632字节SHA256均 `d37a05cd64ac1a25ae12742ae76ccd56e791eb80fa35209314ad9e23c87f693d`，.data/.pdata/.reloc均SHA相等。e6aa→724a二进制只有28字节变化，具体位于COFF TimeDateStamp及3个debug timestamp副本（合计12字节）和RSDS PDB GUID（16字节）；e6aa→548a也仅28字节。这表明不同DLL文件哈希来自构建/调试身份变化，**并未更换实际产品可执行机器码**。即使构建 ISA-L archive hash不同，最终链接的 .text 仍一致。

因此“长测失败是短测后编译成另一份产品逻辑”这一竞争解释被可靠排除；**没有排除同一机器码在600/1800s出现线程/缓存/句柄/内核/网络时变故障，也没有证明 GitHub Runner 实际的失联原因。** 目前三臂 Action42555320138 的真实产品600、干净Windows750、Ubuntu异地状态同时在跑，等待各自真实硬门收据。不重复派发。

```feature-impact
{"kind":"none","ids":[],"reason":"Artifact-level SHA256 and PE section forensic evidence only, no product or network change."}
```
