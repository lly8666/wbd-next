"""H1280: exact original Normal client/server M4 receipt oracle.

An authenticated client-local READY is NOT an independently verified server
Rust M4 start. H1279 pressure Alice had one entire 73s unserved generation.
"""
import importlib.util
import pathlib
import unittest

MODULE=pathlib.Path(__file__).with_name("m0-plan028-h1274-30min-report.py")
SPEC=importlib.util.spec_from_file_location("h1274_report",MODULE)
report=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report)

class NormalM4Proof(unittest.TestCase):
    def test_exact_tuple_and_per_generation_rejection(self):
        client="\n".join([
            "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=10 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1 client_ipv4=10.88.0.2 client_port=54000",
            "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=11 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1 client_ipv4=10.88.0.2 client_port=54001",
        ])
        server="\n".join([
            "V4_PUBLIC_MIXED_NORMAL_READY role=server port=443 client_ipv4=10.88.0.2 client_port=54000 active_normal=3 active_game_groups=2 detached_flows=10 protected_TLS=1 Rust_M4=1",
            # Same source port on a different physical host is not proof.
            "V4_PUBLIC_MIXED_NORMAL_READY role=server port=443 client_ipv4=10.88.0.3 client_port=54001 active_normal=3",
            "V4_PUBLIC_MIXED_ADMISSION_REJECT stage=normal_rust_owner m4_stage=rust_loop_start native_rc=7 class=other client_ipv4=10.88.0.2 client_port=54001",
        ])
        scoped=report.normal_m4_client_proof(client)
        commits,rejects=report.normal_m4_server_proof(server)
        self.assertEqual(scoped,[(10,"10.88.0.2",54000),(11,"10.88.0.2",54001)])
        self.assertIn(("10.88.0.2",54000),commits)
        self.assertNotIn(("10.88.0.2",54001),commits)
        self.assertEqual(rejects[("10.88.0.2",54001)],("rust_loop_start",7))
        self.assertEqual([gen for gen,ip,port in scoped if (ip,port) not in commits],[11])

    def test_missing_server_log_fails_closed(self):
        scoped=report.normal_m4_client_proof(
            "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1 client_ipv4=198.51.100.7 client_port=54002")
        committed,_=report.normal_m4_server_proof("")
        self.assertEqual(len(scoped),1)
        self.assertNotIn((scoped[0][1],scoped[0][2]),committed)
        self.assertEqual(report.normal_m4_client_proof(
            "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3"),[])

if __name__=="__main__":
    unittest.main()
