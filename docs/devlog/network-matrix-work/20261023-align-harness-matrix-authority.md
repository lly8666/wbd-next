# 清除夹具/矩阵中的旧权限与策略矛盾

用户要求直接清除矛盾。本次基于已消费PR25提示词的 `eb81b78a`，只更新NETWORK_HARNESS、NETWORK_MATRIX及本日志，目标仍为 `experiment/network-matrix-tuning`，不合main、不操作其他agent目录。

- 将PR21最初只写测试工具明确为历史范围；自主岗位可修产品/观测/夹具，不等待M0或领取正式角色。当前分工统一指向NETWORK_CURRENT_PLAN，FEC专项不重复开发。
- 复核现有artifacts.py、runner.py、config.py与workflow：ARM64原生路径和TX/RX/M1/部分FEC计数已存在；修复字节、时序及auto曲线仍有缺测。文档区分已接线、NOT_OBSERVED、物理机未验，缺项按实际需要自主补齐。
- 取消强制重跑历史ARM首轮、旧构建来源和完整容量梯子；保留原有产物校验、单Action单场景、同VM比较、容量停止及原失败。
- 同步一次修复策略，移除两次重传作为当前允许上限/容量预算的旧写法；500M例子更新为同假设下约452.0Mbps模型值，不是实测。历史p³/5d保留时明确只作历史解释。
- 补齐TCP背压是有效业务能力观测、单流/多流分别验收、最终残余不等于修复及时、预算按字节与时间窗记账。FEC公式明确发出r与及时到达前提，未改变原数值验收门。

检查diff空白、局部引用、遗留冲突词及改动范围。未改产品、测试代码/请求、workflow或status，未发起Actions；本次不产生新的产品资格。现有产品SOURCE、OPEN与next_action全部保留。
