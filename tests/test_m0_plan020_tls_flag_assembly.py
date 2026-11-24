"""Restores H2214 already accepted default-OFF original Windows CLI TLS switch.

The original donor must be unchanged; assembly and blob are source locked.
No product test can count as successful until actual original Windows build.
"""
import json
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]

class ManifestTlsVerify(unittest.TestCase):
    def test_default_off_in_exact_pinned_original_go_manifest(self):
        d=json.loads((ROOT/"r0/go_overlay/assembly/manifest-plan020-m0.json").read_text())
        self.assertEqual(d["legacy_source"],"a7a82db31fe736ffedee330795a3234d358f1984")
        ops=[op for op in d["operations"] if op["path"]=="cmd/wbd-client/main_windows.go"]
        self.assertEqual(len(ops),1)
        op=ops[0]
        self.assertEqual(op["kind"],"replace")
        self.assertEqual(op["original_blob"],"57f0e5a2d9d3187f36edfa77ec5da8031e9e5cbc")
        self.assertEqual(len(op["result_blob"]),40)
        checks=[p for p in op["patches"] if 'tlsVerifyServer = flag.Bool("tls-verify-server",' in p["replace"]]
        self.assertEqual(len(checks),1)
        self.assertIn('flag.Bool("tls-verify-server", false,',checks[0]["replace"])
        self.assertIn('TLSVerifyServer:*tlsVerifyServer',
                      "\n".join(p["replace"] for p in op["patches"]))
        wf=(ROOT/".github/workflows/m0-plan020-windows-native-os-receipt.yml").read_text()
        self.assertIn('r0/go_overlay/assembly/manifest-plan020-m0.json',wf)
        self.assertIn('PLAN020_H2214_DEFAULT_OFF_SERVER_TLS_VERIFY_FLAG_SOURCE_ASSEMBLED',wf)
        self.assertIn('PLAN020_ORIGINAL_GO_TLS_VERIFY_FLAG_SOURCE_INVALID',wf)
        h2214=(ROOT/"docs/devlog/M0/20261119-H2214-CLIENT-TLS-VERIFY-SWITCH-QA.md").read_text()
        self.assertIn("default OFF",h2214)
if __name__=="__main__":
    unittest.main()
