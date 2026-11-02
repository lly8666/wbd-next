# Linux服务端：最小配置与统一wbd-next管理入口

状态：**PLANNED，仅方案**。2026-11-02用户明确将借站域名加入服务端配置，并要求直接输入 `wbd-next` 管理安装/卸载/配置/客户端/启停。当前PLAN027性能与接线任务不被打断；不更改M0正在运行的SOURCE、cursor或Actions。本能力登记于 `docs/features/entries/server-management-cli.json`，实施时按现有任务机制接续。

## 1. 配置：端口、借站域名、账号密码

建议最小正式配置（尚非当前二进制可用格式）：

```json
{
  "listen": "0.0.0.0:443",
  "server-name": "www.cisco.com",
  "users": [
    { "username": "user1", "password": "自行设置" }
  ]
}
```

- `server-name`沿用老名称，是服务端权威借站域名；客户端连接配置需在TLS开始前拿到并匹配它，不能等认证后才获知。默认示例www.cisco.com，可在菜单修改。常规借站目标端口443从该值推导，不要求用户再填一份decoy。沿用既有真实建链机制，不将自签证书冒充借站网站证书。
- 同账号多终端允许并存，按内部session与分配地址区分；Normal/Game各lane复用一个服务监听端口。客户端地址可自动或请求手动指定，检查占用后安装；租约7天、地址不必持久化，重启重新分配。用户不手填内部route-key/tunnel-id/lane标识，但原认证/隔离职责仍由自动建链逻辑承担。
- FEC off/fixed/auto、加密、模式/lane数、Game发送策略、外层重传、轮换/idle/keepalive、启动填充、期望MTU等在认证后按客户端安装，不是服务端全局固定值；读回实际双向档位和有效MTU。客户端请求受双方支持能力及本地设备MTU约束，不悄悄接受未安装参数。
- 高级可选项只保留服务器自身信息：出口网卡/绑定IP、地址池、状态目录/日志等级，默认自动选择。地址池需避开已有路由；无法合理自动确定时清楚提示用户填一次，不凭空声称所有多网卡拓扑都能自动判断。
- 服务端自身所需证书/私钥首次自动生成并保存，后续启动复用；按用户意向默认100年有效，准确生成/解析并跨支持后端验收，不用溢出的固定秒数计算。它与借站前端握手是不同职责；若当前冷层需要不同证书语义，先复习原流程再接，不靠关闭校验实现简化。
- 不新增线上固定DATA字段或周期管理报文。配置传入继续现有认证控制通道和有限填充；若当前协议无法表达必需项，在既有版本/能力机制中明确安装，不盲猜格式。

当前 `r0/go_overlay/internal/v4productcli/linux.go` 仍要求raw-interface/local-ip/tun-ipv4/server-name/route-key/tunnel-id/cert等，且模式参数启动时安装。**简化配置依赖自动认证/地址与按client安装的实际接线，不能只包装旧命令并硬编码所有客户端同一个ID。**

## 2. 一个命令，两种使用方式

首次解压包后运行 `sudo ./wbd-next`；安装后任何目录运行 `sudo wbd-next`。无参数且有终端时显示简单中文编号菜单，不引入全屏TUI框架。退出菜单不停止后台服务；非交互输入不进入等待菜单，显示用法/状态并退出。

```text
WBD Next 服务端
状态：运行中 / 已停止 / 未安装 / 启动失败
监听：0.0.0.0:443   借站：www.cisco.com
设备：在线 3 · 休眠 1   版本：…

1. 安装并设为开机启动
2. 修改配置（端口 / 借站域名 / 账号密码 / 高级项）
3. 查看客户端信息
4. 启动服务
5. 停止服务
6. 重启服务
7. 查看状态与最近日志
8. 完整卸载
0. 退出
```

同一后端提供直接子命令，方便Actions和脚本，无第二套实现：

| 命令 | 行为 |
|---|---|
| `wbd-next install` | 用当前完整本地包安装、生成配置、注册持久服务并启动 |
| `wbd-next config` | 配置向导，账号增删改在同一入口 |
| `wbd-next config check` | 校验配置，错误不修改正在运行的实例 |
| `wbd-next status [--json]` | 安装/进程/实际监听就绪/配置revision/最近错误；不是只看PID |
| `wbd-next clients [--json] [--watch]` | 一次快照；watch每2秒更新，关闭界面即停止 |
| `wbd-next start/stop/restart` | 调用同一系统服务及原产品Stop，不另起第二个实例 |
| `wbd-next logs` | 有界最近日志，默认100行；跟随仅显式选用 |
| `wbd-next uninstall [--yes]` | 完整移除本程序管理的安装与网络状态；交互仅一次确认 |
| `wbd-next serve --config <path>` | 服务管理器前台运行入口，菜单不能递归启动自己 |

正常停止不取消开机启动；完整卸载会停止并取消。若用户需要暂禁开机启动，可在配置菜单提供开关，不必增加另一组复杂命令。管理动作需要root时显示一条明确说明，不嵌套sudo或反复弹确认。第一版不做在线升级/版本仓库/自动下载/回滚中心/Web管理面。

## 3. 安装与持久服务

优先支持systemd Linux amd64/arm64，复用老部署语义；无systemd明确提示当前安装方式不支持，仍可 `serve` 前台运行，不用nohup冒充持久服务。OpenWrt后续复用已有procd包，不能把systemd测试当作其通过。

- 包含匹配SOURCE的管理/服务程序、Rust库及manifest，按架构与hash安装；不分别下载不匹配的Go/Rust版本，不在线编译或自行装一批系统工具。管理CLI是短命冷控制层，可复用Go，不必为了语言统一重写Rust CLI；稳态仍使用既有Rust数据面。
- 固定布局：`/opt/wbd-next/`程序/配套库/manifest，`/usr/local/bin/wbd-next`入口，`/etc/wbd-next/server.json`配置，`/var/lib/wbd-next/`证书/owned网络恢复记录/安装清单，`/run/wbd-next/`运行时socket/PID，`/etc/systemd/system/wbd-next.service`服务。若用独立轮转日志，统一在 `/var/log/wbd-next/`，默认总量有界。不运行时往随机目录释放二进制。
- 复用systemd监督一个前台服务，`Restart=on-failure`、约3秒退避、SIGTERM有界正常Stop；复用原生ready通知则用`Type=notify`，ready表示监听/本机资源就绪，不等第一位客户端来才启动成功。退出菜单/SSH断开不影响运行，重启系统按已安装配置启动。超时沿产品清理期限配置，不多层无限等候。
- 安装顺序：校验本地包与配置→自动生成缺失的自身材料→写文件/unit→daemon-reload/enable/start→查真实ready。重复install发现已安装则显示状态，不覆盖账号/证书或偷偷重置网络。失败给具体步骤和简短日志。
- 复用旧网络配置/owned恢复；不能整表flush防火墙/路由，不能擅自开放SSH或关闭机器安全策略。自动选择raw出口、TUN/NAT/转发的实际安装效果必须验收；不把unit active当真实客户端可上网。

## 4. 配置修改：简单、明确生效

第一版不做复杂热重载。向导读现有配置，密码输入不回显；修改在内存/临时同目录文件校验，成功才原子替换（失败保留原配置）。保存后若服务运行，明确提示“重启应用，现有连接短暂中断”；可确认立即重启，也可只保存，状态同时显示磁盘/当前revision，不能保存即宣称生效。

端口或借站域名变更后展示新的客户端连接信息；域名需要在握手前同步，旧客户端配置不匹配时不能靠取消匹配校验蒙混通过。凭据不进入进程命令行、日志或默认状态JSON；配置文件按现有私有文件权限保存。已有账户同名修改而非重复追加；多个设备不会因为同用户名被互相踢出。

## 5. 客户端信息：会话汇总，不加热路径负担

默认按逻辑客户端一行，同账号不同设备各一行，Game的2/4条lane不算多个客户端。会话ID给短显示值，内部完整身份继续用于正确归属。

字段：账号、会话/备注（若已有）、隧道IP、远端地址、连接时长、在线/休眠/重建状态、Normal/Game及活动lane数、实际加密、上下行FEC模式/档位、外层/有效内层MTU、累计上下行流量与当前速率、最近真实业务时间。RTT/丢包估计仅当既有有效样本存在时显示数值及样本年龄；fixed/off没有质量样本显示“未知”，不启动Auto/新探针凑界面。

只读已有owner低频快照。已有本机控制入口能复用就复用，否则最小本地Unix socket提供status/clients快照；无外部监听、无常驻额外监控进程、无每包JSON/锁/日志。服务端不因无人看菜单而每2秒额外扫描；watch期间约2秒取样，锁内只取必要快照，格式化在锁外。CLI关闭不影响业务/keepalive/idle。

## 6. 完整卸载的边界与顺序

卸载含程序、配套库、命令入口、unit及开机启用、配置/账号、证书/私钥、缓存/自身日志、runtime文件、安装时本程序创建的TUN/路由/NAT/规则。仅删除安装清单/owned记录中的本程序对象，不能删除其他项目或系统库。

顺序：取消自动重启/开机启动并正常Stop→核网络恢复或调用既有owned恢复→确认进程退出→删除unit并daemon-reload→删除本程序文件及入口，最后删恢复记录/安装清单。安装包由用户下载在别处的不自动搜索删除。sysctl仅按原值与当前归属恢复，不覆盖后来别的程序设置。

网络恢复失败时明确报“卸载未完成”，保留恢复所需程序和记录，重跑同命令继续，不先删WAL导致无法收尾。不全盘清理共享journal；系统审计历史可能仍有服务记录，这不代表程序仍安装。不得为清除此记录删除整机日志。正常一机单实例即可，不设计多代理抢占/极端恶意目录的通用治理框架。

## 7. 实施与简单验收

1. 先复习旧实现，再一次写齐配置/自动材料、服务端按client入口与公共菜单/子命令、unit/打包/功能卡；复用已成熟网络和业务引擎，不改TLS-like/TCP-like wire或稳态算法来迁就菜单。
2. Actions一次构建Linux amd64/arm64包，复用编译产物。功能检查可同Action顺序批量；性能仍一个Action一场景，管理功能不触发整张弱网矩阵。
3. 在真实systemd runner做安装→ready→两个同账号真实客户端同时连接（含不同FEC/加密/MTU；Game同端口）→clients读回→stop/start/restart→有效配置修改和错误配置拒绝→卸载→重装。安装/卸载重复一次，确认无重复规则/账号重置/自身残留；保留其他已有网络设置。
4. 验证enable及unit配置；若CI不能重启宿主，明确“开机启动已配置、真实重启NOT_RUN”，不把重启服务冒充重启系统。arm64原生包需实际加载/运行，无原生环境就标BUILD_ONLY。
5. 确认借站域名在客户端建链前一致，证书重启复用；已认证客户端实际配置分别生效；客户端状态没有把lane数当设备数，休眠不误记掉线，不把无样本记0%丢失。
6. 容量内一次持续业务对照不开菜单/clients-watch，每2秒读取不能显著增加CPU、尾延迟或影响首到；沿用已有低频统计，微小噪声不反复刷测试。凭据/真实业务正文不上传，不留大pcap。

旧源参考（固定 `wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`）：[wbdctl](https://github.com/lly8666/wobuzhidao/blob/a7a82db31fe736ffedee330795a3234d358f1984/deploy/linux/wbdctl)、[服务模板](https://github.com/lly8666/wobuzhidao/blob/a7a82db31fe736ffedee330795a3234d358f1984/deploy/linux/wbd-server.service)、[配置](https://github.com/lly8666/wobuzhidao/blob/a7a82db31fe736ffedee330795a3234d358f1984/deploy/linux/server.example.json)、[地址租约](https://github.com/lly8666/wobuzhidao/blob/a7a82db31fe736ffedee330795a3234d358f1984/internal/logicaltunnel/lease_registry.go)。复用原子配置、打包hash、服务监督及owned恢复语义，不搬旧升级/rollback中心。systemd行为参考[service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)及[执行环境](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)，只用受支持系统上已有的基础功能。
