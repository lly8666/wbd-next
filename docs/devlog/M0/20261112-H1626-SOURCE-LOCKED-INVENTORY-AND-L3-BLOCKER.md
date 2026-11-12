# PLAN028 H1626｜恢复真实Actions与SOURCE锁定的功能清单

先核main原HEAD `60006d13ece22506c4ef9ae930270b5a4fa173aa`。H1625 Feature catalog+Governance Action43113485314和governance-maintenance Action43113485414均 **SUCCESS**；H1575 Action42979705842在真实五端150s UDP/TCP阶段局部通过后，最终共享服务端echo提前退出导致整场**FAIL**，不能改称整场通过；原治理42979705889 FAIL与43112296446 UTF8卡片/缺source_sha FAIL保留。H1624已修feature卡16129 UTF8字节、Evidence product source字段；H1625维护复验成功。本次不删除原失败证据。

正式原Go标准TLS443 + Rust ISA-L native **产品二进制**SOURCE `8a31375e36bb6a93860c5579e64b4a39d0b6e346` **未变**，H1601 Action43027983611一签名Wintun＋四Linux同账号独立安装、自动/32、三AEAD、150s真实双向UDP/TCP、Windows单独Stop后Bob新UDP继续、最后六owners和WAL清理 **PASS_SCOPED**。H1623 Action43110135433相同正式预构件 Windows手动/32+真正Ubuntu WSL2 idle108.48s后60s 99497/99551真业务首次交付、TCP、Stop **PASS_SCOPED**。此前 inventory 把自动租约/AES说成仅编译及Windows冷30%未验，现依据原始H1592/H1601/H1623纠正；不把此类PASS推广所有平台/模式。

L3隔离控制硬前置见 `docs/testing/PLAN028_L3_ISOLATED_CONTROL_PLANE.md`：GitHub-hosted Windows runner 同时是被测 Wintun 主机，WSL2共故障域；缺外部 A控制+B独立 Windows DUT+C独立 Linux 的有效场所，Windows 1800s仍 **INFRA_BLOCKED/NOT_QUALIFIED**，不能重试hosted来刷PASS。另有Win AutoIP物理路径、七模式当前SOURCE代表、高损全业务与CPU/RSS/queue-age/p99未齐；原H1587双Wintun历史route WAL CAS FAIL、此前用户跳过近innerMTU、旧ARM64长测、Linux outer双向总量304Mbps都保留原范围。本批只核对事实和更新inventory/功能卡/覆盖/交接，不变产品、默认、编译或网络场景；028继续IN_PROGRESS、不启动029/030。

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Recovered source-locked Windows signed idle/auto-IP/AES business receipts and corrected outdated feature catalog metadata; no production or default change."}
```

## H1627: Collect H1626 new Actions and separate two historical negative regressions

HEAD `0949ef5143d07d2099011d2d4bfdb601a56a1baa` H1626 [Feature Catalog + Governance Action43129899096](https://github.com/lly8666/wbd-next/actions/runs/43129899096) both **SUCCESS** and [governance-maintenance Action43129899162](https://github.com/lly8666/wbd-next/actions/runs/43129899162) **SUCCESS**; no new product source, binary or network Action. Correct the historical failure classification: Action43112296390 Feature Catalog separately rejected an over-bounded regular-JSON card, while Action43112296446 governance-maintenance regression actually failed its negative tests because missing original product evidence source_sha caused a wrong-SOURCE exception before expected stale-epoch/authorization failures. They are two distinct old FAILs, not both card-size failures. H1624/H1625 corrected metadata and subsequent checks passed without overriding original results. H1575 complete native Action42979705842 remained FAIL after local 150s true business stage, current scoped H1601/H1623 remain PASS_SCOPED. PLAN028 still IN_PROGRESS pending independent real Windows DUT L3/other listed scopes; do not run 029/030.

```feature-impact
{"kind":"none","ids":[],"reason":"Only accurate classification of two historical CI failures and collection of H1626 successful catalog/governance regressions; no new product or feature behavior."}
```
