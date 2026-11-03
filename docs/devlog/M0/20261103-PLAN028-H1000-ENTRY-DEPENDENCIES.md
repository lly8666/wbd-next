# H1000｜PLAN028用户启动与入口依赖核查（未施工完毕）

2026-11-03用户明确调用PLAN028。核对H998限定范围收口、H999治理修复及当前main `ea3b97a973defc8727d12e6ec81937d7877c0abf`：最新governance Action 41566715536为success，所列最近main Actions无在途。**本条只记录源码路径和实施边界：无028产品代码修改、无028 SOURCE构建、无新native PASS。**

## 真实调用链上的差异

- `v4productcli/linux.go` Normal当前只有一个 `V4LinuxServerProduct` 和一次 `AcceptAuthenticatedPeer`，不是单端口多设备常驻accept；冷重连先等Rust dead90并停止旧owner才重建。不能把测试单端口监听误报成多client。
- `game_linux.go:gamePort`按lane递增server/client端口；Game2/4并非一服务端口。`admission_v4.go:V4EpochStore.prepare`同lane活跃时拒绝新建，`ReleaseLane`没有replacement generation fence。简单放宽会让旧退休回调释放新代。
- 客户端CLI仍强制 `--route-key-hex`/`--tunnel-id`，server固定tunnel ID；原始 `hello.go:recognized` 在TLS账号认证**之前**用route-key生成的HMAC识别ClientHello。账号密码字段不能直接替代握手前秘密。不得删除输入验证、使用公开常量、取消原借站识别来伪称手填模式可用。
- 原 `logicaltunnel.LeaseRegistry` 有安装ID派生、7天内存租约与活动保护，需复用；现有V4协议也已有`InstallationID`、`AutoLease`，但公开Linux CLI未把它们接到同一真实owner/地址池。
- `ConfigureTunnelMTU`现在会改当前进程TUN。多人共享server TUN时必须按session/lane方向budget（复用Rust `V4DeriveColdMTUBudget`与MTU_CONTRACT），不得再由最后一个client改全局TUN。普通外层意图默认1460、1500仅显式最大。
- 现有Go overlay需同步`assembly/manifest*.json` hash与原始Go/native bundle复制清单，不能只写一个未装配的新模块。Windows原生路由/WFP/Stop接线也不能以单纯事件注入代替系统级通过。

## 最小接口落点（先确定，不代表已接线）

`ClientIntent`：username + credential reference、自动持久安装ID、numeric endpoint IPv4:port、独立SNI、Normal/Game/FEC/cipher、外层MTU意图（default1460）、自动/手动IP请求。身份/用户配置作用域由会话决定，非server全局变量。保留必要认证材料但不暴露手填隐藏要求。

`AuthenticatedSessionHandle`：服务端在TLS认证后以account+设备绑定的续接凭证授权logical session/租约，区分path_epoch（物理变化）和lane generation（安全密钥）；同账号另一安装ID不得接管。A/B重叠时旧代退休不能释放新IP。保留Rust单owner。

`EndpointSnapshot`：数值endpoint、物理ifindex、源IPv4、路由下一跳/实际已知MTU、时间和path_epoch；系统通知只触发~200ms/最长500ms合并及重新查询，过滤TUN/无关路由，不在热路径DNS/逐包FFI。029消费resolver数值候选，Android入口后来接。

`EffectiveSessionSnapshot`：配置requested outer 1460/显式值、每方向/lane Rust effective outer与inner、OS读回、mode/Auto启动状态、租约、lane status、generation、最后认证/首包时间；readonly，任何变更须有真实安装结果。server TUN全局值另列不得被client覆盖。

测试样本预预算：Normal 5–10Mbps除以1389B完整内IP约450–900 pps/方向；Game4 3Mbps逻辑约276 pps（1358B内包），四副本约1105 lane copies/s再加实际parity，仅规模估算。先同SOURCE真实功能和接管，再量分阶段CPU/p99。500ms只是事件处理窗口不是握手总时限。

**保留H998原结论**：1500→1280真实在线物理缩窄3/3未回应仍FAIL；ARM64 Game4FEC Action FAIL；对端ICMP3/4未测；旧新产品CPU因果未证。028没有新资格，不回跑旧027/027A、不新建恢复器。

下一施工应是整批真实双方认证/会话多路/实际driver接线+测试夹具，SOURCE冻结后一次构建再运行真实OS场景；本条没有完成该工作。
