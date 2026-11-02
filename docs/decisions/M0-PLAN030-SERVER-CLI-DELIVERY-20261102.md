# PLAN030｜服务端管理CLI、打包与组合交付

PLANNED；吸收并替代已撤回的独立 `M0-SERVER-CLI-SIMPLIFICATION-20261102.md`，不是另一项同时施工任务。读[总入口](M0-LEGACY-ROLLOUT-20261102.md)、[提示词](../prompts/M0-PLAN030.md)。配置/账号/IP/单端口语义归028，域名客户端与GUI归029；本包提供薄管理层，不复制业务控制器。

## 1. 最小配置与中文入口

```json
{
  "listen": "0.0.0.0:443",
  "server-name": "www.cisco.com",
  "users": [{ "username": "user1", "password": "自行设置" }]
}
```

借站域名在服务端配置并随客户端连接资料提供，不能等TLS完成后才让客户端知道。网卡/绑定IP/地址池/日志目录为高级可选，默认自动；FEC/cipher/MTU等每client独立，菜单不再提供误导性的全server单档位。默认100年自签证书是内部材料管理选项，首次生成后复用，与已验证借站握手职责分开，不改外层握手来迁就菜单。

MTU遵守[唯一契约](../architecture/MTU_CONTRACT.md)第1节：用户默认外层完整IPv4 IP包上限1460（不含L2，可显式最大1500）；client提交外层完整IP上限，server按自身路径限制自动收窄并计算内层，不增加必填server MTU或内层TUN输入。若已有高级服务端外层上限需要保留，只作本地额外约束且明确标“外层”；不照抄client数值成全局TUN MTU。

首次解压后 `sudo ./wbd-next`，安装后任意目录 `sudo wbd-next`；无参且有终端显示编号菜单，非TTY打印用法/状态退出，不等待输入。退出菜单/SSH断开不停止后台服务。

```text
WBD Next 服务端：运行中/已停止/未安装/启动失败
监听 / 借站域名 / 在线与休眠设备数 / 版本
1 安装并开机启动       2 修改配置
3 查看客户端信息       4 启动服务
5 停止服务             6 重启服务
7 状态与最近日志       8 完整卸载
0 退出
```

同一后端直接命令：`install`、`config`、`config check`、`status [--json]`、`clients [--json] [--watch]`、`start/stop/restart`、`logs`、`uninstall [--yes]`；服务前台入口 `serve --config <path>`。不要两套菜单/命令实现，不加Web后台、在线升级/版本仓库/回滚中心。普通停止不取消开机启动，配置菜单可显式关闭自启，卸载会取消。

## 2. 安装、配置和完整卸载

- 第一版systemd Linux amd64/arm64；OpenWrt复用另有procd包，不强套systemd。无服务管理器可前台运行，不能nohup冒充持久服务。
- 当前本地完整包一次校验架构/SOURCE/manifest/hash，安装匹配的Go冷层+Rust库；不在线编译或混下载不同版本。管理器可复用Go短命冷控制，服务稳态仍是当前Rust路径，不为语言统一重写OS管理。
- 固定自有目录：`/opt/wbd-next/`程序/库，`/usr/local/bin/wbd-next`入口，`/etc/wbd-next/server.json`配置，`/var/lib/wbd-next/`证书/网络恢复记录/安装清单，`/run/wbd-next/`临时socket；unit `/etc/systemd/system/wbd-next.service`，独立日志若有则 `/var/log/wbd-next/`有界轮转。不运行时随机释放二进制。
- 复用原systemd模板：单前台服务、ready通知、失败约3s退避、SIGTERM原owned Stop；期限沿当前实际清理能力，不能多层无限等待。ready只要求本机监听资源就绪，不等第一位client来。安装是校验→生成缺失材料→写unit→enable/start→真实状态读回；重复install不重置账号/证书/网络。
- 配置向导调用028统一验证，临时同目录写入后原子替换。第一版保存后提示显式重启生效，磁盘与运行revision可区分；不做复杂热更新。密码不回显/不进进程参数/默认状态日志。端口/site变化展示需要更新的客户端连接资料。
- uninstall只确认一次（自动化可--yes）：disable并Stop→恢复本程序owned TUN/路由/NAT/规则→确认进程退出→删unit并daemon-reload→删本程序文件/配置/证书/缓存/自有日志/入口，最后恢复记录与清单。失败保留必要恢复材料，明确未完成；不先删WAL，不flush整机路由/防火墙。sysctl按原值与当前归属恢复，不覆盖后来别的设置。
- 不搜索删除用户另存的安装包/其他程序或系统库，不为“清干净”清空共享journal。按一机一个代理实例，正常取消/恢复须好用，不扩建极端多实例/恶意目录防御框架。

旧源固定 `a7a82db31fe736ffedee330795a3234d358f1984`：[wbdctl](https://github.com/lly8666/wobuzhidao/blob/a7a82db31fe736ffedee330795a3234d358f1984/deploy/linux/wbdctl)、[service](https://github.com/lly8666/wobuzhidao/blob/a7a82db31fe736ffedee330795a3234d358f1984/deploy/linux/wbd-server.service)、[配置](https://github.com/lly8666/wobuzhidao/blob/a7a82db31fe736ffedee330795a3234d358f1984/deploy/linux/server.example.json)。搬成熟配置/包校验/owned恢复语义，去掉旧在线升级中心；systemd细节按[官方service文档](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)核对，不引入不必要的新版本依赖。

## 3. 客户端信息与冷层成本

同账号不同设备各一行，Game四lane仍一个设备。复用028 ClientSnapshot，展示账号/短session、隧道IP、远端IP、连接时长、在线/休眠/重建、模式/活动lane数、实际加密、上下行FEC、外层/内层MTU、流量/速率、最近真实业务。RTT/丢包仅有既有有效样本才显示并注明年龄；fixed/off无样本显示未知，不为菜单启动Auto或探针。

MTU列区分“client外层设置上限 / 方向有效外层 / 自动内层与OS应用状态”，均来自已有快照；菜单不提供内层调节，不另算公式。客户端默认外层1460与Normal/off示例内层1389之类不同值是正常派生，不能显示为配置错误；数字只在对应模式/约束成立时如此，不写成固定转换。

已有本机控制入口优先复用；若缺，仅一个本地Unix socket提供只读快照，无外部管理端口/新守护进程。默认一次快照；--watch才每2s读取，锁内只取必要数据、锁外格式化，不每包JSON/全局遍历。无人查看不新加监控循环，菜单不能影响业务idle/keepalive。

## 4. 并行与测试

028配置/快照接口确定后，菜单、unit、安装包可并行开发；真实多client/effective验证必须接028实际产品。029的GUI/DNS可独立Actions并行，汇合只做受影响组合，禁止把mock session验收当账号/IP已完成。

代码/双方配置入口/unit/包/help/功能卡齐再构建一次。普通功能可同Action顺序批量，性能一Action一场景：

1. systemd安装→真实ready→同账号两个实际client（不同模式/FEC/cipher/MTU，同端口）→clients正确→stop/start/restart→有效配置变更与无效配置拒绝→uninstall→重装。确认无重复规则/账号重置/自身残留，其他网络设置保留。
2. arm64包实际加载/运行，amd64同源功能；没有原生环境标BUILD_ONLY。校验enable/服务模板，但不能重启CI宿主时，真实机器重启留NOT_RUN，不拿restart服务冒充重启OS。
3. 组合场景用域名连接且Windows DNS劫持已开启，完成一次重连/轮换，server客户端列表身份/IP/effective正确，回收旧lane不误删另设备。七模式完整换lane证据复用028，本包不再刷七条。
4. 一个容量内持续业务同VM对照不开菜单/clients --watch，查看CPU/RSS/首到/p99。已有低频快照复用，无显著异常即可，不为1%噪声做多轮优化，不重跑大带宽矩阵。
5. 所有临时网络状态owned清理；凭据/业务正文/大pcap不上传。读回命令失败给短可定位错误，不只返回unit active或菜单已保存。

退出：实际可安装/服务化/管理/清理，连接资料与每client配置有效，CLI/help/配置/功能卡一致，027/028/029证据按SOURCE/平台/模式明确引用；不宣称物理或未测OpenWrt PASS。只有此包被启动就交付此包；若整个序列已授权且全部完成，提示待验收并停止扩测。
