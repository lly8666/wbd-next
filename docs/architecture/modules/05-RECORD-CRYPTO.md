# 05 独立record、AEAD和去重

## 固定格式

沿用原record编码：外头5B=`0x17 0x03 0x03 body_len:u16`；protected PN8B；密文和16B tag。明文=`kind:u8 || payload || 0x17 || zero_padding`。基础总成本31B。不能把PlainFixedLen误写成payload length字段，不能把末尾业务零字节当padding截断。

nonce=IV12异或`00000000 || PN_be64`；AAD=实际外头5B+未掩码PN8B。ChaCha HP采样ciphertext前16B：前4B作little-endian counter，后12B作nonce，HPKey32生成8B mask。AES HP用独立HPKey对同16B做一次AES block，取前8B；AES128只用该方向派生key的前16B，AES256用32B。包括极短记录时，HP sample可以覆盖tag，与原代码一致。不得用QUIC只产生5B的HP API硬代替。

## 实现选择

aws-lc-rs非FIPS `UnboundKey + LessSafeKey`，使用显式nonce的原地seal/open；这是为独立乱序record所选接口，不使用有序TLS record key或每次随机nonce API。key/context每lane方向只建一次。HP raw AES/ChaCha采用RustCrypto对应原语，只承担这8B mask，选择运行时硬件分派，不重复new key schedule。

封装`LaneTxCrypto`只归TX，`LaneRxCrypto`只归RX，无共享可变cipher mutex。PN预留后，无论后续容量/加密/系统发送失败均不回退；到最大值触发换lane而不是wrap。repair输入只能是FrozenRecord，不接受plain slice，从类型上禁止重加密。

TX步骤：预算和slice长度检查→预留PN→写kind/payload/marker/padding→生成AAD/nonce→原地seal→生成HP并写PN→freeze。RX步骤：检查外头/长度/当前最大wire→取HP恢复PN→生成AAD/nonce→原地open→验证kind/末尾marker/padding→去重→交LINK/Health。认证失败后buffer内容不可信，直接回收，不用于再次解析业务。

一个TCP payload含多完整record时按length前进；长度可信但AEAD失败只跳当前record，长度越界则停止剩余payload，避免扫字节猜边界。正常第一版不打包多个业务record来等待攒包。开启有限startup padding继续原规则，padding有效长度进入MTU账。

## 真实去重窗口

取`N=nextpow2(PN_rate × max(Tcache+2R, FEC_horizon+2R) ×1.25)`，再受metadata总预算限制。以256PN一page、page tag验证的滑动bitmap实现，不用每PN hash map。只有AEAD成功的PN能推进max_seen；巨大跳跃须按认证lane的有效PN域与资源限额处理，不一次无界清空数组。

窗口内第一次置位可交付、重复仅用于必要receipt重申；低于明确retired floor计Late并拒绝，不能忘记历史后又当新业务交付。这是有限寿命承诺，支持的最大重排序/修复时间写进effective config；如果capacity限制缩短窗口必须报告，不能偷偷缩成65536后在高PPS重复交付。bitmap页面按epoch惰性清理，跳跃不for遍历全部PN。

该窗口用于lane record重放；Game/FEC/fragment各自逻辑去重不能省掉。跨lane密文不同，必须先各自验证再共享shard。默认不做“只看未认证PN就跳过AEAD”的捷径；若以后优化已知完全相同密文，需独立证据，不在首版加入第二套指纹状态。

## 测试与失败

旧V3全部golden保留为兼容数学向量；V4新KDF另有双语言golden。三cipher、长度0/1/15/16/17/MTU边界、padding0/极限、篡改各字段、PN失败后不复用、乱序/重复/回绕临界、错direction/key/generation、4lane相同业务密文不能相同。SIMD与generic结果逐字节一致；检测是否硬件加速和实际CPU收益分开。

参考：[aws-lc-rs AEAD接口](https://docs.rs/aws-lc-rs/latest/aws_lc_rs/aead/index.html)及旧 `tlsrecord/{record,keys,suite,decoder}.go`。原库建议的随机nonce API不适用于本协议既定wire；这是有意选择，不是遗漏。
