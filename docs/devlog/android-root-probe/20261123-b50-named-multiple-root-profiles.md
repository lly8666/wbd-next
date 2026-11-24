# B50｜原Android Root常用多配置：四套命名连接/模式/UID及DNS快速切换

## B49 资格与本批目标
B49 SOURCE `344594efcf893bfae93f737ae4c62fa9a1956e47` [Android Dual64 #45168583911](https://github.com/lly8666/wbd-next/actions/runs/45168583911) **11 SUCCESS / 4 SKIPPED**；治理卡容量修复 `18ad0a60e1d3` [#45168843972](https://github.com/lly8666/wbd-next/actions/runs/45168843972) 成功。此前 Normal 真机原SYN/TLS/租约/M4/owned Stop已有分层收据；最新Game/B49真机业务和CPU仍 NOT_RUN/NOT_PROVEN。

B50完成单个大类「常用连接多配置」实际生产接线，非诊断或防御增强：
1. 新 `RootConnectionProfile` 直接嵌套现有 `RootConnectionSettings.write/read`，保存原Server/SNI/账户/外层MTU/AEAD/Normal-Fixed-Auto-Game2/4、FEC档、Health、三DNS及所选实体Network跟随DNS选项、IPv4直连、当前App UID组或all-app绕过。四个命名本机槽位独立保存于无备份目录；单配置不含Root权限、密码、RouteKey、CA或历史Network handle。原SharedPreferences秘密存储不改。
2. 正式Activity新增选槽、填名字、保存、载入、删除，**载入仅替换冷UI表单**；支持与B49前台一键切网按现有 `start()` 共用业务路径。载入后更新原最后连接缓存，重新从本机PackageManager核对同包名同UID，原Go真实TLS/租约/Rust M4/UID route/owned Stop照旧由用户START触发。
3. 修真正的已有产品缺口：`restoreConnectionSettings` 此前 `restoredSelection.putAll` 与已选复选框合并，切换不同预设可能把旧App UID混进新连接。现在先清旧选中/旧bypass后应用新配置，再按真实当前包UID重建复选框；旧Go/Rust网络数据面不变。
4. `RootConnectionProfileTest` 纯JVM覆盖四类Normal/Auto/Game、FEC/MTU/Health/IPv4 CIDR/包UID及名称编码并检测不包含密码/Key/Network；复用已有源锁Host与签名ARM64 App Gate，无新重型工作流、不操作手机与公网Server。

本SOURCE是否有同源双ABI/签名APK/Linux原Oracle资格，以对应 Action 的实际Job为准；物理Android切换、多配置真实START、逐字节App TCP/UDP、Game和性能全部 **NOT_RUN/NOT_PROVEN**。仅实验分支与Draft PR #36；main/M0不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B50四套命名Root连接配置复用原B22 serializer/UID冷复核，载入仅替换UI表单、修跨配置旧UID复选框残留；原Go/Rust业务/Stop不变。"}
```

## B50 自动CI真实失败（保留，不改记）

B50 SOURCE `e5b4334b712208e94b1caa28c460de3f45aa12c0` [dual64 #45171551179](https://github.com/lly8666/wbd-next/actions/runs/45171551179) 的 `root-arm64-app` **FAIL**：正式APK javac 发现新增 `TextView profileHint` 与已有 `onCreate` 同名变量重定义；所有B50纯JVM多配置测试和源静态门先前已PASS，仍没有此SOURCE签名APK。B51新SOURCE仅将新局部变量改名 `namedProfileHint`，原设置存储与Go/Rust不改；新产品构建需独立验收。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"记录B50 root-arm64-app真Java局部变量重名FAIL并在B51仅改新控件变量名，保留失败证据与原产品逻辑。"}
```
