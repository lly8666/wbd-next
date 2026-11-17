"""B3 pure source guards: real kernel IPv6 + original IPv4, not route-only PASS."""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
class Plan029BRealIPv6(unittest.TestCase):
    def test_original_wintun_first_byte_ipv6_is_distinct_and_fair(self):
        io=(ROOT/"crates/wbd-platform/src/windows_native_io.rs").read_text()
        runtime=(ROOT/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
        self.assertIn("if data[0] >> 4 == 6 {",io)
        self.assertIn("Ok(ReadResult::SkippedIpv6)",io)
        branch=runtime.split("Ok(ReadResult::SkippedIpv6)=>{",1)[1].split("},",1)[0]
        self.assertIn("captured+=1;",branch)
        self.assertIn("counters.skipped_ipv6.fetch_add(1,Ordering::Relaxed)",branch)
        self.assertNotIn("NativeDecision::Tunnel",branch)
        self.assertIn("PLAN029B_WINTUN_IPV6_SKIPPED_STOP packets={}",runtime)
        game=(ROOT/"crates/wbd-engine/src/v4_windows_game_native_runtime.rs").read_text()
        self.assertIn("Ok(ReadResult::Skipped|ReadResult::SkippedIpv6)=>{",game)
        self.assertIn("Ok(ReadResult::Skipped|ReadResult::SkippedIpv6)=>continue,",game)
        self.assertIn("c.rejected.fetch_add(1,Ordering::Relaxed);",game)
    def test_all_three_original_nonproduct_plan029_probe_readers_handle_ipv6_skip(self):
        # H2106 library-only Rust tests omit m0_v4_probe, while original
        # signed Windows release always enables it. Each probe keeps its
        # existing wait/break semantics: IPv6 NEVER reaches IPv4 decode.
        parts={
            "udp":"Ok(ReadResult::Skipped|ReadResult::SkippedIpv6|ReadResult::NoPacket|ReadResult::EndOfStream)=>{",
            "tcp":"Ok(ReadResult::NoPacket|ReadResult::Skipped|ReadResult::SkippedIpv6|ReadResult::EndOfStream)=>break,",
            "dns":"Ok(ReadResult::Skipped|ReadResult::SkippedIpv6|ReadResult::NoPacket|ReadResult::EndOfStream)=>{",
        }
        for name,arm in parts.items():
            with self.subTest(name=name):
                file=ROOT/("crates/wbd-engine/src/v4_windows_plan029_"+name+"_gate.rs")
                text=file.read_text()
                self.assertIn('feature="m0_v4_probe"',text)
                self.assertIn(arm,text)
        wf=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("Windows source-locked PLAN029 probe cargo check",wf)
        self.assertIn("cargo +1.85.1 check --locked --release",wf)
        self.assertIn("--features m0_v4_embedded_go,m0_v4_probe,fec2_product_record --lib",wf)
    def test_real_windows_os_owned_route_and_kernel_send_with_cleanup(self):
        win=(ROOT/"tools/m0_plan029b_b3_ipv6_windows.py").read_text()
        guest=(ROOT/"tools/m0_plan029b_b3_ipv4_guest.py").read_text()
        ast.parse(win)
        ast.parse(guest)
        self.assertIn('SRC6="fd73:29b:2026::2"',win)
        self.assertIn('PREFIX=DST6+"/128"',win)
        self.assertIn("Get-NetAdapterBinding",win)
        self.assertNotIn("Disable-NetAdapterBinding",win)
        self.assertNotIn("Set-NetAdapterBinding",win)
        self.assertIn("New-NetIPAddress -InterfaceIndex IDX",win)
        self.assertIn("New-NetRoute -InterfaceIndex IDX",win)
        self.assertIn("Remove-NetRoute -AddressFamily IPv6",win)
        self.assertIn("Remove-NetIPAddress -AddressFamily IPv6",win)
        self.assertIn("socket.AF_INET6",win)
        self.assertIn("six.sendto(datagram,(DST6,46115))",win)
        self.assertIn("four.recvfrom(256)",win)
        self.assertIn("sent6!=16 or got4!=12",win)
        self.assertIn('row.get("source_sha")!=os.environ.get("GITHUB_SHA")',win)
        self.assertIn("PLAN029B_B3_LINUX_TUN_IPV4_READY",guest)
    def test_original_b3_never_claims_global_host_ipv6_and_always_cleans_route(self):
        harness=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
        self.assertIn('int(skips[0])<16',harness)
        self.assertIn('"physical_bound_onlink_ipv6":"NOT_PROVEN_BLOCKED"',harness)
        self.assertIn('"global_ipv6_leak_claim":False',harness)
        self.assertIn('owned.get("cleanup")!="PASS_EXACT_TEST_OWNED_IPV6_ADDRESS_ROUTE_ABSENT"',harness)
        self.assertIn('if p029b_b3 and (out/"plan029b-b3-owned-ipv6-route.json").exists():',harness)
        # Source is a test-scoped /128; never assert physical-bound or
        # on-link bypass flows are globally intercepted by Wintun.
    def test_only_one_real_windows_signed_normal_scene_original_owned_stop(self):
        e2e=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
        workflow=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        ast.parse(e2e)
        self.assertIn('WBD_PLAN029B_B3_IPV6_SCENE',e2e)
        self.assertIn('PLAN029B_B3_ORIGINAL_WINDOWS_REAL_IPV6_IPV4',e2e)
        self.assertIn('PLAN029B_WINTUN_IPV6_SKIPPED_STOP packets=',e2e)
        self.assertIn('PASS_SCOPED_REAL_AF_INET6_WINTUN_IPV4_MIX_AND_STOP',e2e)
        self.assertIn('[plan029b-b3-ipv6-real]',workflow)
        self.assertIn('WBD_PLAN029B_B3_IPV6_SCENE:',workflow)
        self.assertIn('tests.test_m0_plan029b_b3_ipv6_scope',workflow)
        self.assertIn('WBD_PLAN029_D4_IPV6_SCENE:',workflow)
        self.assertIn("default1460",workflow)

if __name__=="__main__":
    unittest.main()
