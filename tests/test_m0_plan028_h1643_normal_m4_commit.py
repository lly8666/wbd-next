"""Exact-source normal A->A+B->B server M4 oracle; no network. H1642 raw ZIP.
A client-local READY, cold TLS, B_PENDING, or truncated Health is NOT proof.
"""
import importlib.util
import pathlib
import unittest

PATH=pathlib.Path(__file__).resolve().parents[1]/"tools/m0-plan028-h1286-rapid-report.py"
SPEC=importlib.util.spec_from_file_location("h1643_h1286_report",PATH)
REPORT=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


def log(ip="10.25.0.2",first=41031,second=56872):
    return "\n".join((
        f"V4_PUBLIC_MIXED_NORMAL_READY role=server port=443 client_ipv4={ip} client_port={first} active_normal=1 protected_TLS=1 Rust_M4=1",
        "V4_PUBLIC_NORMAL_TUN_CANDIDATE_DEFERRED role=server generation=13 old_route_preserved=1",
        "V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=off profile=0 cipher=2 authenticated_TLS=1 original_Rust_M4=1",
        f"V4_PUBLIC_MIXED_NORMAL_PEER_PERSONA role=server client_port={second} selected=0 cold_syn_known=true authenticated_TLS=1 original_Rust_M4=1",
        f"V4_PUBLIC_MIXED_NORMAL_B_PENDING role=server client_port={second} old_route_preserved=1 authenticated_client_M4_required=1",
        "V4_PUBLIC_NORMAL_SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX generation=13 verified_client_cold_health=1 old_route_preserved_until_proof=1",
        f"V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server client_port={second} source=authenticated_client_native_Health promoted=1 active_normal=3 old_route_preserved_until_proof=1"
    ))


class NativeServerM4Commit(unittest.TestCase):
    def test_initial_and_authenticated_b_success(self):
        first,b,deny=REPORT.normal_m4_server_proof(log())
        self.assertEqual(first,{("10.25.0.2",41031)})
        self.assertEqual(b,{56872})
        self.assertFalse(deny)
        self.assertTrue(REPORT.normal_m4_proven("10.25.0.2",41031,first,b,{41031:1,56872:1}))
        self.assertTrue(REPORT.normal_m4_proven("10.25.0.2",56872,first,b,{41031:1,56872:1}))
        self.assertFalse(REPORT.normal_m4_proven("10.25.0.99",56872,first,b,{56872:1}))
        self.assertFalse(REPORT.normal_m4_proven("10.25.0.2",56872,first,b,{56872:2}))
        self.assertFalse(REPORT.normal_m4_proven("10.25.0.2",56873,first,b,{56873:1}))

    def test_missing_native_health_or_promotion_fails(self):
        original=log()
        for replacement in (
            ("source=authenticated_client_native_Health","source=unverified_local_READY"),
            ("promoted=1","promoted=0"),
            ("verified_client_cold_health=1","verified_client_cold_health=0"),
            ("original_Rust_M4=1","original_Rust_M4=0"),
            ("authenticated_TLS=1","authenticated_TLS=0"),
            ("old_route_preserved=1 authenticated_client_M4_required=1",
             "old_route_preserved=1 authenticated_client_M4_required=0"),
        ):
            with self.subTest(replacement=replacement):
                initial,b,deny=REPORT.normal_m4_server_proof(original.replace(*replacement))
                self.assertNotIn(56872,b)
                self.assertFalse(REPORT.normal_m4_proven("10.25.0.2",56872,initial,b,{56872:1}))
                self.assertFalse(deny)

    def test_out_of_order_and_missing_stage_fails(self):
        text=log()
        fragments=text.splitlines()
        mutated="\n".join(fragments[:3]+[fragments[4],fragments[3]]+fragments[5:])
        _,b,_=REPORT.normal_m4_server_proof(mutated)
        self.assertFalse(b)
        _,b,_=REPORT.normal_m4_server_proof(text.replace(
            "V4_PUBLIC_NORMAL_SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX generation=13 verified_client_cold_health=1 old_route_preserved_until_proof=1",""))
        self.assertFalse(b)

    def test_server_rejection_is_not_softened(self):
        txt=log()+("\nV4_PUBLIC_MIXED_ADMISSION_REJECT stage=normal_rust_owner "
                 "m4_stage=postauth native_rc=-3 class=invalid client_ipv4=10.25.0.2 client_port=56872")
        _,b,deny=REPORT.normal_m4_server_proof(txt)
        self.assertIn(56872,b)
        self.assertEqual(deny[("10.25.0.2",56872)],("postauth",-3))


if __name__=="__main__":
    unittest.main()
