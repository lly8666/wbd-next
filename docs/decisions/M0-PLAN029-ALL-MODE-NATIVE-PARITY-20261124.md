# PLAN029 H2397 · 全模式原生设施统一

用户授权：Windows TX16/NPF64KiB 默认开启；公平准入覆盖所有原生产品客户端/服务端/模式；移植已有快解析和可共享的原生批服务；一次集中修改后验证实际正常 TCP/UDP 与 owned Stop，不跑 A/B 或吞吐矩阵。基线 39cf1ae，短分支 `experiment/m0-029-all-mode-native-parity`。Linux x86/ARM 所有 Normal/Game 租约共享原满队列公平规则与128槽；Windows Wintun 内核 FIFO 没有可替换未读包接口，在已有 ready batch 内按相同五元组公平服务，不人为丢包、不增加等待线程。Windows 产品支持客户端，正式服务端 Linux；不宣称新增Windows服务端产品。保持原 FEC/PN/密文、ACK、driver copied prefix、MTU、Stop；仅复用现有算法，实际未验边界保留。已知实验负结果/BBR2/全局OS TCP模板不移植。功能回归七模式，Linux原生两ISA、Windows signed NPF/Wintun 对Linux，假红按原始回执判定。
