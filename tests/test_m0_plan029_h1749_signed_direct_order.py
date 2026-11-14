"""PLAN029 signed physical Direct evidence before unrelated TCP comparator."""
import unittest
from pathlib import Path
S=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_public_normal_e2e.py").read_text(encoding="utf-8")
class NativeDirectOrder(unittest.TestCase):
    def test_signed_direct_before_inbound_tcp_comparator_but_after_udp(self):
        self.assertLess(S.index(' report["actual_kernel_udp"]=real'),S.index('  # D1/D2 real physical Direct first'))
        self.assertLess(S.index('  # D1/D2 real physical Direct first'),S.index(' # Functional-only *real TCP*'))
        self.assertLess(S.index(' # Functional-only *real TCP*'),S.index(' report["tcp_duplex"]="PASS_ACTUAL_TWO_OS_KERNEL_TCP"'))
    def test_no_early_two_exits_or_false_stop(self):
        self.assertLess(S.index('PLAN029_H1749_SIGNED_CN_DNS_FAKE_DIRECT_UDP_STAGE_PASS_PRE_TCP_AND_STOP'),S.index('PLAN029_H1760_SIGNED_CN_DIRECT_TCP_32K_TWO_LEG_HALF_CLOSE_PASS_PRE_TUNNEL_AND_STOP'))
        self.assertLess(S.index('PLAN029_H1760_SIGNED_CN_DIRECT_TCP_32K_TWO_LEG_HALF_CLOSE_PASS_PRE_TUNNEL_AND_STOP'),S.index('PLAN029_H1749_SIGNED_CN_DIRECT_AND_TUNNEL_TCP_UDP_STAGE_PASS_PRE_STOP'))
        self.assertLess(S.index('PLAN029_H1749_SIGNED_CN_DIRECT_AND_TUNNEL_TCP_UDP_STAGE_PASS_PRE_STOP'),S.rindex('\n stop_windows(w)\n'))
        self.assertIn('"tunnel_tcp":"NOT_RUN_PRE_TCP_COMPARATOR"',S)
        self.assertIn('m0_plan029_h1760_guest_physical_direct_tcp.py',S)
        self.assertIn('m0_plan029_h1760_windows_fakeip_direct_tcp.py',S)
        self.assertIn('owned-wal.json.plan029-defender-tcp',S)
        self.assertIn('report["plan029_private_v3_cn_direct_tcp"]["stop"]',S)
        self.assertIn('source_address=(local,0)',S)
        self.assertIn('result["dial_source"]=conn.getsockname()[0]',S)
        self.assertIn('result["dial_source"]!=local',S)
        self.assertIn('proof["tunnel_tcp"]=report["tcp_duplex"]',S)
        self.assertIn('raise RuntimeError("real public TCP apps failed;',S)
        self.assertIn('"stop":"NOT_RUN_UNTIL_OWNED_STOP"',S)
    def test_exact_windows_linux_physical_receipts(self):
        for term in ['m0_plan029_h1745_guest_dns_direct.py','m0_plan029_h1745_win_client_dns_direct.py','gdata["business_client_physical"]==host_source','gdata["dns_client_physical"]==host_source','"source_sha":os.environ["GITHUB_SHA"]','WBD_PLAN029_NATIVE_V3_TRIAL']:
            self.assertIn(term,S)
    def test_h1764_tcp_core_rust_change_triggers_exact_signed_scope_only(self):
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        for path in (
            "crates/wbd-engine/src/v4_windows_native_tcp_direct.rs",
            "crates/wbd-engine/src/v4_client_direct_tcp_nat.rs",
            "crates/wbd-engine/src/v4_windows_native_split.rs",
            "crates/wbd-engine/src/v4_windows_native_runtime.rs",
            "crates/wbd-platform/src/windows_direct_tcp.rs",
        ):
            self.assertIn("      - "+path,W)
        self.assertIn("[plan029-v3-real-direct-udp]",W)
        self.assertIn("WBD_PLAN029_V3_DIRECT_SCENE",W)
        self.assertIn("PLAN029_H1762_GUEST_TCP46112_HYPERV_EXACT_OWNER_REMOVED",W)
    def test_h1762_wsl_exact_physical_tcp_owner_and_scoped_comparator(self):
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        M=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_mode_evidence.py").read_text(encoding="utf-8")
        self.assertIn("PLAN029_H1762_PHYSICAL_GUEST_TCP46112_HYPERV_EXACT_ALLOW_READBACK",W)
        self.assertIn("-LocalPorts '46112'",W)
        self.assertIn("$directName=$ruleName+'-P029-TCP46112'",W)
        self.assertIn("Remove-NetFirewallHyperVRule -Name $name -ErrorAction Stop",W)
        self.assertIn("PLAN029_H1762_GUEST_TCP46112_HYPERV_EXACT_OWNER_REMOVED",W)
        self.assertIn("result/wl-public/hyperv-direct-tcp-owned.json",W)
        self.assertIn('plan029-h1760-guest-physical-tcp.log',M)
        self.assertIn('plan029-h1760-windows-fakeip-tcp.log',M)
        self.assertIn('m0_plan029_h1762_oneway_tunnel_tcp.py',S)
        self.assertIn('PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP',S)
        self.assertIn('historical_028_linux_to_windows_tcp',S)
    def test_h1765_scoped_real_noncn_tunnel_dns_and_safe_process_cleanup(self):
        import ast
        ast.parse(S)  # the full original signed Windows E2E runner must compile
        self.assertNotIn("  wa,li=json.loads(a[0]),json.loads(b[0])",S)
        self.assertIn("  tcp_windows_receipt,li=json.loads(a[0]),json.loads(b[0])",S)
        self.assertIn("PLAN029_H1765_SIGNED_NONCN_UDP53_TUNNEL_DNS_SINGLE_ENDPOINT_PASS_SCOPED",S)
        self.assertLess(S.index("PLAN029_H1762_SIGNED_DIRECT_TCP_UDP_ONEWAY_TUN_TCP_UDP_PASS_PRE_STOP"),S.index("PLAN029_H1765_SIGNED_NONCN_UDP53_TUNNEL_DNS_SINGLE_ENDPOINT_PASS_SCOPED"))
        self.assertIn("plan029-h1765-owned-tunnel-dns-alias.txt",S)
        self.assertIn("PLAN029_H1765_TUNNEL_DNS_ALIAS_CLEANUP_FAILED",S)
        self.assertIn('if dns_alias in wsl("ip","-4","-o","addr","show","dev","wbdwl4",timeout=8)',S)
        self.assertIn('wsl("ip","-4","addr","del","1.1.1.1/32","dev","wbdwl4",timeout=8)',S)
        self.assertIn('"app_tcp53":"NOT_RUN"',S)
        M=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_mode_evidence.py").read_text(encoding="utf-8")
        self.assertIn('plan029-h1765-linux-tun-dns.log',M)
        self.assertIn('plan029-h1765-windows-tun-dns.log',M)
        for path in ("tools/m0_plan029_h1765_linux_tun_dns.py",
                     "tools/m0_plan029_h1765_windows_tunnel_dns.py"):
            source=(Path(__file__).resolve().parents[1]/path).read_text(encoding="utf-8")
            ast.parse(source)
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        self.assertIn('      - tools/m0_plan029_h1765_linux_tun_dns.py',W)
        self.assertIn('      - tools/m0_plan029_h1765_windows_tunnel_dns.py',W)
    def test_h1784_target_only_tunnel_dns_ignores_other_qnames_but_not_foreign_target(self):
        import ast
        src=(Path(__file__).resolve().parents[1]/
             "tools"/"m0_plan029_h1765_linux_tun_dns.py").read_text()
        module=ast.parse(src)
        fn=next(n for n in module.body if isinstance(n,ast.FunctionDef)
                and n.name=="is_target_question")
        # Execute only the tiny pure QNAME predicate, never import its
        # actual bound real Linux DNS/53 socket during a cheap self-test.
        ns={"question":b"\x03www\x07globalx\x07example\x00\x00\x01\x00\x01"}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),
                     "<H1784 DNS filter>","exec"),ns)
        target=(b"\x17\x65\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                +ns["question"])
        self.assertTrue(ns["is_target_question"](target))
        self.assertFalse(ns["is_target_question"](target[:-4]+b"\x00\x1c\x00\x01"))
        self.assertFalse(ns["is_target_question"](target[:12]+
            b"\x07another\x07example\x00\x00\x01\x00\x01"))
        self.assertFalse(ns["is_target_question"](b"\x00"*8))
        self.assertIn("if not is_target_question(query):",src)
        self.assertIn("if unrelated>64:",src)
        self.assertIn("if peer[0]!=client:",src)
        self.assertLess(src.index("if not is_target_question(query):"),
                        src.index("if peer[0]!=client:"))
        self.assertIn("deadline=time.monotonic()+26",src)
        self.assertIn('"unrelated_dns_ignored":unrelated',src)
        self.assertIn('"target_queries":1',src)
        self.assertIn("listener.sendto(response,peer)",src)
    def test_h1766_outer_scope_accepts_only_true_029_tunnel_dns_and_tcp(self):
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        self.assertIn("elseif($env:WBD_PLAN029_V3_DIRECT_SCENE -eq '1')",W)
        self.assertIn("$result.tcp_duplex -ne 'PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP'",W)
        self.assertIn("$dns.linux.upstream_ip -ne '1.1.1.1'",W)
        self.assertIn("$dns.windows.reply_source -ne '8.8.8.8'",W)
        self.assertIn("$direct.windows.app_bytes_echoed -ne 32768",W)
        self.assertIn("$direct.stop -ne 'PASS_OWNED_DEFENDER_AND_WAL_ABSENT'",W)
        self.assertIn("PLAN029_H1766_OUTER_SOURCE_LOCKED_DIRECT_TUNNEL_DNS_TCP_UDP_AND_STOP_PASS_SCOPED",W)
        for path in (
            "crates/wbd-engine/src/v4_client_startup_padding.rs",
            "crates/wbd-engine/src/v4_owner_crypto.rs",
            "crates/wbd-engine/src/v4_windows_owner.rs",
            "crates/wbd-engine/src/lib.rs",
        ):
            self.assertIn("      - "+path,W)
        self.assertIn("$result.tcp_duplex -ne 'PASS_ACTUAL_TWO_OS_KERNEL_TCP'",W)
        self.assertLess(W.index("} elseif($env:WBD_PLAN029_V3_DIRECT_SCENE -eq '1')"),
                        W.index("selected same-SOURCE native public mode lacks actual two-OS UDP/TCP/Stop proof"))
    def test_h1767_one_selected_dns_blackhole_no_direct_fallback(self):
        import ast
        ast.parse(S)
        self.assertLess(S.index("PLAN029_H1765_SIGNED_NONCN_UDP53_TUNNEL_DNS_SINGLE_ENDPOINT_PASS_SCOPED"),
                        S.index("PLAN029_H1767_SIGNED_NONCN_DNS_TUNNEL_BLACKHOLE_ZERO_DIRECT_FALLBACK_PASS_SCOPED"))
        self.assertLess(S.index("PLAN029_H1767_SIGNED_NONCN_DNS_TUNNEL_BLACKHOLE_ZERO_DIRECT_FALLBACK_PASS_SCOPED"),
                        S.rindex(" stop_windows(w);stop_linux()"))
        for proof in ('"tunnel_query_count"', '"physical_query_count"', '"unexpected_response"',
                      'bh_proofs["linux"]["client_source"]==["10.66.0.2"]',
                      '"blackhole_no_fallback"'):
            self.assertIn(proof,S)
        self.assertIn('p029_dns_blackhole_guest,p029_dns_blackhole_win',S)
        M=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_mode_evidence.py").read_text(encoding="utf-8")
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        for path in ("tools/m0_plan029_h1767_linux_dns_blackhole.py",
                     "tools/m0_plan029_h1767_windows_dns_blackhole.py"):
            source=(Path(__file__).resolve().parents[1]/path).read_text(encoding="utf-8")
            ast.parse(source)
            self.assertIn("      - "+path,W)
        for basename in ("plan029-h1767-linux-dns-blackhole.log",
                         "plan029-h1767-windows-dns-blackhole.log"):
            self.assertIn(basename,M)
        self.assertIn("$result.plan029_d1_dns_blackhole_no_fallback.source_sha -ne $env:GITHUB_SHA",W)
        self.assertIn("$result.plan029_d1_dns_blackhole_no_fallback.linux.physical_query_count -ne 0",W)
    def test_h1769_d1_blackhole_filters_unrelated_qnames_without_hiding_real_fallback(self):
        # The physical and TUN listeners share real OS ports with preceding
        # work; unrelated CN/OS queries are not the target nonCN fallback.
        source=(Path(__file__).resolve().parents[1]/
                "tools"/"m0_plan029_h1767_linux_dns_blackhole.py").read_text(encoding="utf-8")
        self.assertIn('query[12:12+len(expected)]!=expected',source)
        self.assertIn('unrelated[key.data]+=1',source)
        self.assertIn('receipts[key.data]+=1',source)
        self.assertLess(source.index('unrelated[key.data]+=1'),
                        source.index('receipts[key.data]+=1'))
        self.assertIn('if receipts["tunnel"]<2 or receipts["physical"]!=0:',source)
        self.assertIn('"unrelated_query_count":unrelated',source)
        self.assertIn('if peer[0]!=lease:raise RuntimeError',source)
        # Exact DNS encoded question length must match the Windows app.
        w=(Path(__file__).resolve().parents[1]/
           "tools"/"m0_plan029_h1767_windows_dns_blackhole.py").read_text(encoding="utf-8")
        self.assertIn(r'\x09no-backup\x07globalx\x07example\x00',source)
        self.assertIn(r'\x09no-backup\x07globalx\x07example\x00',w)
    def test_h1770_real_noncn_dns_answer_is_used_by_original_tunnel_app(self):
        import ast
        ast.parse(S)
        self.assertLess(S.index("PLAN029_H1765_SIGNED_NONCN_UDP53_TUNNEL_DNS_SINGLE_ENDPOINT_PASS_SCOPED"),
                        S.index("PLAN029_H1770_SIGNED_NONCN_DNS_REAL_A_FOLLOWED_BY_TRUE_TUNNEL_UDP_PASS_SCOPED"))
        self.assertLess(S.index("PLAN029_H1770_SIGNED_NONCN_DNS_REAL_A_FOLLOWED_BY_TRUE_TUNNEL_UDP_PASS_SCOPED"),
                        S.index("PLAN029_H1767_SIGNED_NONCN_DNS_TUNNEL_BLACKHOLE_ZERO_DIRECT_FALLBACK_PASS_SCOPED"))
        self.assertIn('d2_real=dns_proofs["windows"]["real_answer"]',S)
        self.assertIn('d2_real!=dns_proofs["linux"]["reply_a"]',S)
        self.assertIn('d2_receipts["linux"]["source_lease"]=="10.66.0.2"',S)
        self.assertIn('"cn_ip_a_converse":"NOT_RUN"',S)
        self.assertIn('p029_d2_tun_guest,p029_d2_tun_win',S)
        M=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_mode_evidence.py").read_text(encoding="utf-8")
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        for path in ("tools/m0_plan029_h1770_linux_resolved_noncn_tunnel_udp.py",
                     "tools/m0_plan029_h1770_windows_resolved_noncn_tunnel_udp.py"):
            ast.parse((Path(__file__).resolve().parents[1]/path).read_text(encoding="utf-8"))
            self.assertIn("      - "+path,W)
        self.assertIn('plan029-h1770-linux-noncn-a-business.log',M)
        self.assertIn('plan029-h1770-windows-noncn-a-business.log',M)
        self.assertIn("$result.plan029_d2_noncn_resolved_a_tunnel_business.source_sha -ne $env:GITHUB_SHA",W)
    def test_h1770_tcp53_framing_is_bounded_source_only_not_product_claim(self):
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        wire=(Path(__file__).resolve().parents[1]/"crates"/"wbd-engine"/"src"/"v4_client_split_wire.rs").read_text(encoding="utf-8")
        tcp=(Path(__file__).resolve().parents[1]/"crates"/"wbd-engine"/"src"/"v4_client_dns_tcp_ingress.rs").read_text(encoding="utf-8")
        self.assertIn('pub(crate) fn dns_question',wire)
        self.assertIn('mod dns_tcp_ingress;',wire)
        self.assertIn('const MAX_QUESTION_WIRE:usize=2048-42;',tcp)
        self.assertIn('TcpClientDnsFramingError::ExtraPayload',tcp)
        self.assertIn('application TCP/53',tcp)
        self.assertIn("      - crates/wbd-engine/src/v4_client_dns_tcp_ingress.rs",W)
        self.assertIn('"app_tcp53":"NOT_RUN"',S)
    def test_h1770_pinned_legacy_tls_is_reused_only_if_exact_git_source_bytes(self):
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-plan013-windows-rust-original-owner-abi.yml").read_text(encoding="utf-8")
        self.assertIn('assert filename=="tls.go"',W)
        self.assertIn('target.read_bytes()==original_tls',W)
        self.assertIn('pinned original Go TLS mutated by an unowned author',W)
        self.assertIn('M0_PINNED_ORIGINAL_GO_TLS_REUSED_NO_OVERWRITE',W)

    def test_h1775_noncn_dns_to_exact_cn_ip_physical_direct_and_owned_cleanup(self):
        import ast
        ast.parse(S)
        self.assertIn('p029_converse_cn4="198.19.254.2"',S)
        self.assertIn('"--china-ip-file",str(out/"plan029-h1775-cn-one32.txt")',S)
        self.assertLess(S.index("PLAN029_H1770_SIGNED_NONCN_DNS_REAL_A_FOLLOWED_BY_TRUE_TUNNEL_UDP_PASS_SCOPED"),
                        S.index("PLAN029_H1775_REAL_NONCN_TUNNEL_DNS_CN_IP_PHYSICAL_DIRECT_UDP_PASS_PRE_CLEANUP"))
        self.assertLess(S.index("PLAN029_H1775_REAL_D2_CN_IP_CONVERSE_OWNED_CLEANUP_PASS"),
                        S.index("PLAN029_H1767_SIGNED_NONCN_DNS_TUNNEL_BLACKHOLE_ZERO_DIRECT_FALLBACK_PASS_SCOPED"))
        self.assertIn('p029_d2_cn_guest,p029_d2_cn_win',S)
        self.assertIn('h1775_owned_cleanup()',S)
        self.assertIn('"PASS_EXACT_ROUTE_ALIAS_CLEANUP"',S)
        self.assertIn('report["plan029_h1775_owned_cleanup"]="FAIL_OWNED_ROUTE_ALIAS"',S)
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text()
        M=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_mode_evidence.py").read_text()
        for name in ("m0_plan029_h1775_guest_cn_converse.py","m0_plan029_h1775_windows_cn_converse.py"):
            ast.parse((Path(__file__).resolve().parents[1]/"tools"/name).read_text())
            self.assertIn("      - tools/"+name,W)
        self.assertIn("plan029-h1775-linux-cn-converse.log",M)
        self.assertIn("$result.plan029_d2_noncn_cn_ip_direct_udp.source_sha -ne $env:GITHUB_SHA",W)
    def test_h1778_real_bounded_direct8_capacity_and_new_tunnel_isolation(self):
        import ast
        ast.parse(S)
        self.assertIn('p029_pressure=os.environ.get("WBD_PLAN029_DIRECT_PRESSURE")=="1"',S)
        self.assertIn('args.extend(["--direct-flow-hard","8"])',S)
        self.assertLess(S.index("PLAN029_H1775_REAL_D2_CN_IP_CONVERSE_OWNED_CLEANUP_PASS"),
                        S.index("PLAN029_H1778_SIGNED_DIRECT8_NEW_TUNNEL_OLD_DIRECT_RECOVERY_PASS_PRE_STOP"))
        self.assertLess(S.index("PLAN029_H1778_SIGNED_DIRECT8_NEW_TUNNEL_OLD_DIRECT_RECOVERY_PASS_PRE_STOP"),
                        S.index("PLAN029_H1767_SIGNED_NONCN_DNS_TUNNEL_BLACKHOLE_ZERO_DIRECT_FALLBACK_PASS_SCOPED"))
        self.assertIn('report["plan029_d3_direct_hard_pressure"]["stop"]="PASS_BOTH_OWNED"',S)
        self.assertIn('p029_pressure_guest,p029_pressure_win,p029_tcp53_guest,p029_tcp53_win):',S)
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text()
        M=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_mode_evidence.py").read_text()
        self.assertIn("WBD_PLAN029_DIRECT_PRESSURE:",W)
        self.assertIn("$p.windows.unanswered_new_direct -lt 8",W)
        for n in ("m0_plan029_h1778_guest_bounded_flow_pressure.py",
                  "m0_plan029_h1778_windows_bounded_flow_pressure.py"):
            ast.parse((Path(__file__).resolve().parents[1]/"tools"/n).read_text())
            self.assertIn("      - tools/"+n,W)
        self.assertIn("plan029-h1778-linux-flow-pressure.log",M)
    def test_h1779_target_only_dns_listener_preserves_real_cn_ip_direct(self):
        import ast
        src=(Path(__file__).resolve().parents[1]/
             "tools"/"m0_plan029_h1775_guest_cn_converse.py").read_text()
        ast.parse(src)
        self.assertIn('if len(wire)<12 or wire[4:6]!=b"\\x00\\x01" or wire[12:]!=question:',src)
        self.assertIn('unrelated_dns+=1',src)
        self.assertIn('if unrelated_dns>64:',src)
        self.assertIn('if peer[0]!=lease:raise RuntimeError("exact H1775 target DNS',src)
        self.assertIn('"unrelated_dns_ignored":unrelated_dns',src)
        self.assertLess(src.index('unrelated_dns+=1'),src.index('if peer[0]!=lease:'))
        self.assertIn('if peer[0]!=host or wire!=marker:',src)
        self.assertIn('if not seen_dns or not seen_biz:raise RuntimeError',src)
    def test_h1783_signed_native_direct_cn_cache_not_fake_two_clients(self):
        import ast
        ast.parse(S)
        self.assertIn('p029_cache=os.environ.get("WBD_PLAN029_DNS_CACHE_SCENE")=="1"',S)
        self.assertIn("PLAN029_H1783_REAL_CN_DNS_CACHE_TWO_APP_CLIENTS_ONE_UPSTREAM_PASS_PRE_STOP",S)
        self.assertIn('report["plan029_d3_cn_native_dns_cache"]["stop"]="PASS_BOTH_OWNED"',S)
        root=Path(__file__).resolve().parents[1]
        for n in ("m0_plan029_h1745_guest_dns_direct.py",
                  "m0_plan029_h1745_win_client_dns_direct.py"):
            source=(root/"tools"/n).read_text()
            ast.parse(source)
            if n.endswith("_win_client_dns_direct.py"):
                self.assertIn('environ.get("WBD_PLAN029_DNS_CACHE_SCENE")',source)
            else:
                self.assertIn('cache_mode=sys.argv[3]=="1"',source)
                self.assertNotIn('environ.get("WBD_PLAN029_DNS_CACHE_SCENE")',source)
        workflow=(root/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("WBD_PLAN029_DNS_CACHE_SCENE:",workflow)
        self.assertIn("$cache.linux.target_dns_count -ne 1",workflow)
    def test_h1785_guest_cache_mode_is_explicit_wsl_argv_not_parent_env(self):
        import ast
        ast.parse(S)
        self.assertIn('peer,host_source,"2" if p029_multia else "1" if p029_cache else "0"]',S)
        guest=(Path(__file__).resolve().parents[1]/"tools"/
               "m0_plan029_h1745_guest_dns_direct.py").read_text()
        ast.parse(guest)
        self.assertIn('if len(sys.argv)!=4 or sys.argv[3] not in ("0","1","2"):',guest)
        self.assertIn('multia_mode=sys.argv[3]=="2"',guest)
        self.assertIn('cache_mode=sys.argv[3]=="1"',guest)
        self.assertNotIn('environ.get("WBD_PLAN029_DNS_CACHE_SCENE")',guest)
        self.assertIn('time.monotonic()-settled_at>=2.5',guest)
        self.assertIn('if cache_mode and observed["target_dns_count"]!=1:',guest)
    def test_h1807_d3_multia_real_requires_distinct_fakes_and_two_os_stop(self):
        import ast
        ast.parse(S)
        root=Path(__file__).resolve().parents[1]
        guest=(root/"tools"/"m0_plan029_h1745_guest_dns_direct.py").read_text()
        win=(root/"tools"/"m0_plan029_h1745_win_client_dns_direct.py").read_text()
        ast.parse(guest);ast.parse(win)
        self.assertIn('answer_count=3 if multia_mode else 2',guest)
        self.assertIn('socket.inet_aton("203.0.113.89")',guest)
        self.assertIn('if multia_mode:observed["multi_a_answers"]+=1',guest)
        self.assertIn('expected=2 if multia_mode else 1',win)
        self.assertIn('len(set(addresses))!=expected',win)
        self.assertIn('p029_multia=os.environ.get("WBD_PLAN029_D3_MULTIA_SCENE")=="1"',S)
        self.assertIn('report["plan029_d3_multia_real"]["stop"]="PASS_BOTH_OWNED"',S)
        self.assertIn('len(set(fakes))!=2',S)
        workflow=(root/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("WBD_PLAN029_D3_MULTIA_SCENE:",workflow)
        self.assertIn("PLAN029_H1807_REAL_CN_CNAME_TWO_A_TWO_FAKEIP_DIRECT_UDP_OWNED_STOP_PASS_SCOPED",workflow)
        self.assertIn("$m.stop -ne 'PASS_BOTH_OWNED'",workflow)
        self.assertIn("$m.linux.target_dns_count -ne 1",workflow)
    def test_h1791_signed_default1460_original_two_os_readback_and_stop(self):
        import ast
        ast.parse(S)
        self.assertIn('p029_outer1460=os.environ.get("WBD_PLAN029_REAL_DEFAULT_OUTER1460")=="1"',S)
        self.assertIn('if native_outer=="default1460":',S)
        self.assertIn('index=args.index("--mtu");del args[index:index+2]',S)
        self.assertIn('native_outer!="default1460" or windows_inner!=1389:',S)
        self.assertIn('if inner!=1389:',S)
        self.assertIn('p["stop"]="PASS_BOTH_OWNED"',S)
        w=(Path(__file__).resolve().parents[1]/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("WBD_PLAN029_REAL_DEFAULT_OUTER1460:",w)
        self.assertIn("[plan029-v3-real-default1460]",w)
        self.assertIn("$m.real_windows_auto_inner -ne 1389",w)
        self.assertIn("$m.real_linux_auto_inner -ne 1389",w)
    def test_h1794_real_tcp53_one_owned_kernel_backend_two_linux_dns_exits(self):
        import ast
        ast.parse(S)
        self.assertIn('p029_tcp53=os.environ.get("WBD_PLAN029_APP_TCP53_SCENE")=="1"',S)
        self.assertIn('p029_tcp53_guest,p029_tcp53_win):',S)
        self.assertIn('report["plan029_d1_original_app_tcp53"]["stop"]="PASS_BOTH_OWNED"',S)
        self.assertIn("PLAN029_H1794_REAL_ORIGINAL_APP_TCP53_BOTH_ENDPOINTS_PASS_PRE_STOP",S)
        self.assertLess(S.index("PLAN029_H1775_REAL_D2_CN_IP_CONVERSE_OWNED_CLEANUP_PASS"),
                        S.index("PLAN029_H1794_REAL_ORIGINAL_APP_TCP53_BOTH_ENDPOINTS_PASS_PRE_STOP"))
        self.assertLess(S.index("PLAN029_H1794_REAL_ORIGINAL_APP_TCP53_BOTH_ENDPOINTS_PASS_PRE_STOP"),
                        S.index("PLAN029_H1767_SIGNED_NONCN_DNS_TUNNEL_BLACKHOLE_ZERO_DIRECT_FALLBACK_PASS_SCOPED"))
        root=Path(__file__).resolve().parents[1]
        for name in ("m0_plan029_h1794_linux_real_tcp53.py",
                     "m0_plan029_h1794_windows_real_app_tcp53.py"):
            source=(root/"tools"/name).read_text()
            ast.parse(source)
            self.assertIn("PLAN029_H1794_",source)
        workflow=(root/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("WBD_PLAN029_APP_TCP53_SCENE:",workflow)
        self.assertIn("H1794 exact owned physical Linux guest DNS TCP53",workflow)
        self.assertIn("PLAN029_H1794_EXACT_TCP53_PHYSICAL_RULE_RECOVERED",workflow)
        self.assertIn("PLAN029_H1794_REAL_APP_TCP53_DIRECT_AND_TUNNEL_TWO_OS_OWNED_STOP_PASS_SCOPED",workflow)
        self.assertIn("-LocalPorts '53'",workflow)
        self.assertIn("result/wl-public/hyperv-direct-dns-tcp-owned.json",workflow)
        evidence=(root/"tools/m0_wl_mode_evidence.py").read_text()
        self.assertIn('plan029-h1794-linux-two-tcp53.log',evidence)
        self.assertIn('plan029-h1794-windows-app-tcp53.log',evidence)
    def test_h1799_startup_pad_normal_tunnel_only_npf_copied_receipt(self):
        import ast
        ast.parse(S)
        self.assertIn('WBD_PLAN029_STARTUP_PADDING_SCENE',S)
        self.assertIn('args.extend(["--startup-padding","flows"])',S)
        self.assertIn('WBD_PLAN029_M1_STARTUP_PADDING_NPF_RECEIPT',S)
        self.assertIn('"stop":"PASS_BOTH_OWNED"',S)
        self.assertIn('PLAN029_H1799_SIGNED_NORMAL_FLOWS_M1_NPF_PAD_AND_BOTH_OS_STOP_PASS_SCOPED',S)
        workflow=(Path(__file__).resolve().parents[1]/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn('WBD_PLAN029_STARTUP_PADDING_SCENE:',workflow)
        self.assertIn('PLAN029_H1799_SIGNED_NORMAL_M1_PADDING_FLOWS_NPF_COPIED_BOTH_OS_STOP_PASS_SCOPED',workflow)
    def test_h1817_p1_both_real_native_legs_and_exact_prebuilt_source_gate(self):
        import ast
        root=Path(__file__).resolve().parents[1]
        p=(root/"tools/m0_plan029_h1814_p1_tunnel_ab.py").read_text()
        ast.parse(p)
        w=(root/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        for marker in ("[plan029-v3-real-p1-tunnel-ab]",
                       "[plan029-v3-real-p1-reuse]",
                       "WBD_PLAN029_P1_AB_SCENE",
                       "PLAN029_H1814_P1_SIGNED_NORMAL_V4_V3_SAME_VM_CPU_GIB_RTT_P99_GAP_STOP_PASS_SCOPED"):
            self.assertIn(marker,w)
        for marker in ("A_off_old_tunnel","B_on_all_tunnel",
                       "windows_cli_sha256","linux_server_sha256",
                       'report.get("linux_binary_source")!=os.environ.get("WBD_WL_BINARY_SOURCE")',
                       '(side=="linux" and app_source not in (None,SOURCE))',
                       "windows_cpu_seconds_per_actual_delivered_gib",
                       "PASS_SCOPED_P1_BOTH_TRUE_NATIVE_TUNNEL_LEGS_MEASURED"):
            self.assertIn(marker,p)
        self.assertIn("git diff --name-only $sha $env:GITHUB_SHA",w)
        self.assertIn("assert len(b)>100000 and hashlib.sha256(b).hexdigest()==m['sha256'][key]",w)
        self.assertIn("h1814_exact_native_accel",w)
        self.assertIn("assert m['native_fec_acceleration'] is True",w)
        self.assertIn('assert m["source_sha"]==os.environ["LINUX_BINARY_SRC"]',w)
        self.assertIn("PASS_BOTH_OWNED",p)
    def test_h1819_p1_source_frozen_moderate_normal_single_vm_two_legs(self):
        import json
        root=Path(__file__).resolve().parents[1]
        cfg=json.loads((root/"scenarios/plan029-p1-normal-50m-25ms0-60s.json").read_text())
        self.assertEqual(cfg["public_mode"],"normal")
        self.assertEqual(cfg["duration_s"],60)
        self.assertEqual(cfg["tun_mtu"],1460)
        for direction in ("windows_to_linux","linux_to_windows"):
            row=cfg[direction]
            self.assertEqual((row["offered_mbps"],row["delay_ms"],row["loss_pct"]),(50,25,0))
            self.assertEqual([x["udp_payload_bytes"] for x in row["packet_mix"]],[96,1200])
            self.assertEqual(sum(x["packets_weight"] for x in row["packet_mix"]),100)
        h=(root/"tools/m0_plan029_h1814_p1_tunnel_ab.py").read_text()
        self.assertIn('("A_off_old_tunnel","0"),("B_on_all_tunnel","1")',h)
        self.assertIn('report.get("linux_binary_source")!=os.environ.get("WBD_WL_BINARY_SOURCE")',h)
        self.assertIn('app_source not in (None,SOURCE)',h)
        self.assertIn('windows_cpu_seconds_per_actual_delivered_gib',h)
        self.assertIn('oneway_p99":"NOT_MEASURED_UNCALIBRATED_CROSS_OS_CLOCKS',h)
    def test_h1820_real_source_built_v3_export_before_signed_native_driver(self):
        root=Path(__file__).resolve().parents[1]
        w=(root/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        rust=(root/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
        self.assertIn('pub unsafe extern "C" fn wbd_m0_win_native_v3_start(',rust)
        self.assertIn('#[cfg(feature="m0_v4_probe")]',rust)
        self.assertIn("[plan029-v3-real-p2-rebuild]",w)
        self.assertIn("if($env:WBD_PLAN029_NATIVE_V3_TRIAL -eq '1')",w)
        self.assertIn("$features+=',m0_v4_probe'",w)
        self.assertIn('getattr(d,"wbd_m0_win_native_v3_start")',w)
        self.assertIn("PLAN029_H1820_ACTUAL_WINDOWS_DLL_V3_START_EXPORT_AND_LOAD_PASS",w)
        self.assertLess(w.index("PLAN029_H1820_ACTUAL_WINDOWS_DLL_V3_START_EXPORT_AND_LOAD_PASS"),
                        w.index("Full public-run signed original Npcap and Wintun driver install"))
    def test_h1821_exact_v3_export_qualified_prebuilt_reuse_no_old_dll(self):
        w=(Path(__file__).resolve().parents[1]/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("43574002456",w)
        self.assertIn("b7b688573326580e39571c1e748663b8566d5fc2",w)
        self.assertIn("PLAN029_H1821_REUSED_V3_NATIVE_DLL_ABI_REAL_EXPORT_PASS",w)
        self.assertIn("m0_v4_embedded_go,fec2_product_record,native_fec_acceleration,m0_v4_probe",w)
        self.assertIn("getattr(native,'wbd_m0_win_native_v3_start',None)",w)
        self.assertIn("assert len(b)>100000 and hashlib.sha256(b).hexdigest()==m['sha256'][key]",w)
        for key in ("WBD_WL_REUSE_RUN_ID:","WBD_WL_BINARY_SOURCE:","LINUX_BINARY_SRC:"):
            env_line=next(s for s in w.splitlines() if s.strip().startswith(key))
            self.assertIn("b7b688573326580e39571c1e748663b8566d5fc2" if key!="WBD_WL_REUSE_RUN_ID:" else "43574002456",env_line)
            self.assertNotIn("c262636c81d688e8df8e844b668bbcc57957425d",env_line)
if __name__=="__main__":unittest.main()
