# PLAN027A H940｜M4历史不可变、M0当前manifest哈希更新

H939 source `13423742920cd0b9eea6b026c64f2a37cea33c4c` 自动 `governance-maintenance` run41443906446 FAIL：`test_m4_frozen_windows_main_import.py` 用历史 `M0_AUTHORIZED_CURRENT["r0/go_overlay/assembly/manifest.json"]=2f2476...` 比对当前 manifest Git blob，因 H932 同一user default1460对原Go/GUI/PARAMETERS精确patch，当前真实blob=`25b6a9469613d38019acf913707fa42a0aaa588b`。本批仅更新 **M0 current hash** 的该一项；34个 `PINNED_FILES` M4冻结历史 SHA、独立PLAN020 manifest/legacy source从未改写。旧FAIL仍保留，等待本新SOURCE证明恢复。

另收 H937 Windows owner ABI source `07cfeeb793d7f43a719bc7424d0671a1510f6960` run41443312153 完整 PASS：MSVC真实owner M1/M3 v5准备/绑定/Stop及原 Go凭证TLS与DLL打包、Go原始client/server编译。该build/unit资格不宣称Windows↔WSL七模式OS-applied/MTU/DF/弱网通过；原始source adc18d75 Fixed rc1 FAIL和后续 in-flight 不改记。

```feature-impact
{"kind":"none","ids":[],"reason":"Adjust only test's authorized current M0 manifest content hash after approved default1460 source-locked changes, retain frozen historic M4 pins and exact product bytes; no product/feature modification."}
```
