"""B5 one-source one-VM two real Windows/WSL2 10Mbps arms, not old V4/V3 or mock p99."""
import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class B5SameVM(unittest.TestCase):
 def test_real_original_scope_and_bounded_two_arm_measurement(self):
  script=(ROOT/"tools/m0_plan029b_b5_samevm.py").read_text()
  ast.parse(script)
  for value in (
   "PLAN029B_B5_TRUE_SAMEVM_ARM_BEGIN", "WBD_WL_PUBLIC_MODES=\"normal\"",
   "B_split_requested_all", "A_split_off_all", "WBD_PLAN029_NATIVE_V3_TRIAL=\"0\"",
   "WBD_PLAN029B_B5_ARM=arm", "first_delivery_ok_for_scenario",
   "actual_delivered_gib", "windows_cpu_seconds_per_actual_delivered_gib",
   "real_udp_p99_ms", "real_rtt_replies", "cpu_user_s", "cpu_kernel_s",
   "peak_rss_bytes", "PASS_BOTH_OWNED",
   "PASS_SCOPED_B5_TRUE_SAME_VM_10MBPS_TWO_NATIVE_ARMS_MEASURED",
   '"small_tcp_p99":"NOT_RUN"', "same_original_windows_and_linux_binary_sha256"):
   self.assertIn(value,script)
  self.assertIn("SCENE = \"scenarios/plan027a-h941-normal-1460-10m-25ms-loss0-60s.json\"",script)
  self.assertIn("if PAIR.exists():",script)
  self.assertIn("subprocess.Popen([sys.executable,\"-u\",",script)
  self.assertIn('original.wait(timeout=470)',script)
  self.assertNotIn("WBD_WL_PERF_AB_GO_STEADY",script)

 def test_original_go_rust_public_v3_config_same_dns_and_no_direct(self):
  e2e=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
  workflow=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
  scope=(ROOT/"tools/m0_native_ci_scope.py").read_text()
  ast.parse(e2e)
  for need in (
    'p029b_b5=os.environ.get("WBD_PLAN029B_B5_SAMEVM_SCENE")=="1"',
    'if p029b_b5:',
    'args.extend(["--dns.direct",peer,"--dns.tunnel","10.66.0.1"])',
    '"WBD_PLAN029B_B5_ARM"]=="requested_all"',
    'args.extend(["--split-enable","--cn-domain-direct=false"])',
    '"all" if p029_v3 or p029b_b5 else "bypass-lan"'):
   self.assertIn(need,e2e)
  for need in ("[plan029b-b5-samevm-10m]","WBD_PLAN029B_B5_SAMEVM_SCENE:",
               "tools/m0_plan029b_b5_samevm.py",
               "PLAN029B_B5_SAME_VM_10MBPS_CPU_GIB_RSS_UDP_P99_PASS_SCOPED",
               "result/wl-public/plan029b-b5-samevm/"):
   self.assertIn(need,workflow)
  self.assertIn("[plan029b-b5-samevm-10m]",scope)
  self.assertNotIn("[plan029b-b5-samevm-10m] [plan029b-b4-gui-three-real]",workflow)

if __name__=="__main__":
 unittest.main()
