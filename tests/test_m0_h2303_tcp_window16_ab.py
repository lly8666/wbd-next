"""H2303 archived original signed Windows/ARM 8/16/8MiB test-only window comparator."""
import os
import pathlib
import subprocess
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class H2303OriginalTCPWindow16(unittest.TestCase):
    def test_16mib_is_real_kernel_socket_test_not_wbd_queue(self):
        environment=dict(os.environ,
            WBD_H2286_PRODUCT_FULL_WIN_ARM="1",
            WBD_H2302_WINDOW_ABA="1",
            WBD_H2302_BASE_BYTES="8388608",
            WBD_H2302_TUNED_BYTES="16777216",
            WBD_H2302_INNER_TCP_TEST_BYTES="16777216")
        python="import sys;sys.path.insert(0,'tools');import m0_wl_loss_tcp_probe as p;print(p.WINDOW_TEST_BYTES)"
        proc=subprocess.run([sys.executable,"-c",python],cwd=ROOT,env=environment,
                            capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(proc.stdout.strip(),"16777216")
        environment["WBD_H2302_INNER_TCP_TEST_BYTES"]="33554432"
        invalid=subprocess.run([sys.executable,"-c",python],cwd=ROOT,env=environment,
                               capture_output=True,text=True)
        self.assertNotEqual(invalid.returncode,0)
        self.assertIn("H2302_UNSUPPORTED_TEST_WINDOW",invalid.stderr)

    def test_no_stage_intent_at_module_import(self):
        environment=dict(os.environ,
            WBD_H2286_PRODUCT_FULL_WIN_ARM="1",
            WBD_H2302_WINDOW_ABA="1")
        environment.pop("WBD_H2302_INNER_TCP_TEST_BYTES",None)
        p=subprocess.run([sys.executable,"-c",
            "import sys;sys.path.insert(0,'tools');import m0_wl_loss_tcp_probe as p;print(p.WINDOW_TEST_BYTES)"],
            cwd=ROOT,env=environment,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout.strip(),"2097152")

    def test_strict_window_ab_and_product_source_scope(self):
        w=(ROOT/".github/workflows/qa-h2303-win-arm-tcp-window16-loss5.yml").read_text()
        trial=(ROOT/"tools/m0_h2293_true_product_fec_loss.py").read_text()
        arm=(ROOT/"tools/m0_h2286_arm_product.py").read_text()
        for needle in ('WBD_H2302_WINDOW_ABA: "1"',
                       'WBD_H2302_BASE_BYTES: "8388608"',
                       'WBD_H2302_TUNED_BYTES: "16777216"',
                       'WBD_H2294_OFF_REPAIR_ABA: "0"',
                       "[m0-029-h2303-window16-loss5]",
                       "H2302_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE",
                       "PASS_H2302_MEASURED_ORIGINAL_TCP_WINDOW_ABA_FEC_OFF_SCOPED",
                       "h2302_same_vm_tcp_window_abaprime",
                       "==[8388608,16777216,8388608]",
                       "H2302_ARCHIVED_WINDOWS_DLL_SOURCE_BOUNDARY_NOT_CURRENT_PRODUCT",
                       "H2302_ARCHIVED_ARM_SOURCE_BOUNDARY_NOT_CURRENT_PRODUCT",
                       "client_owned_stop","kernel_relay_qdisc"):
            self.assertIn(needle,w)
        for needle in ("H2303_WINDOW_ABA_ONLY_2_TO_8_OR_8_TO_16_MIB",
                       "H2302_WINDOWS_REAL_TCP_SOCKET_READBACK",
                       "H2302_REAL_ARM_ACCEPTED_TCP_RCVBUF_NOT_APPLIED",
                       "H2302_WINDOW_ALONE_WITH_FEC_REPAIR_OFF",
                       "h2302_window_bytes(tag)"):
            self.assertIn(needle,trial)
        self.assertIn('ns("sysctl","-w",key+"=16777216")',arm)

if __name__=="__main__":
    unittest.main()
