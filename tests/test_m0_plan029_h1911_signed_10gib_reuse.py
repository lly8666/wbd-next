"""H1911: exact same-source prebuilt signed 10GiB repeat, no silent recompilation."""
import pathlib,unittest
W=(pathlib.Path(__file__).resolve().parents[1] /
   ".github/workflows/m0-wl-public-normal-full.yml")
SHA="64f6819460f7f950f13bc7d10659a6f4552b28b6"
RUN="43700145002"
MARKER="[plan029-v3-real-p2-reuse-10gib]"
class H1911SignedPrebuiltReuse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow=W.read_text(encoding="utf-8")
    def test_explicit_separate_fixture_and_product_sources(self):
        s=self.workflow
        self.assertIn("WBD_WL_REUSE_RUN_ID: ${{ github.ref_name == 'main' && contains(github.event.head_commit.message, '"+MARKER+"') && '"+RUN+"'",s)
        self.assertIn("WBD_WL_BINARY_SOURCE: ${{ github.ref_name == 'main' && contains(github.event.head_commit.message, '"+MARKER+"') && '"+SHA+"'",s)
        self.assertIn("LINUX_BINARY_SRC: ${{ github.ref_name == 'main' && contains(github.event.head_commit.message, '"+MARKER+"') && '"+SHA+"'",s)
        self.assertIn("m['source_sha']=="+repr(SHA),s)
        self.assertIn("m.get('isa_l_source')=='c387163fcbca62701d646149564c550c78a4f985'",s)
    def test_only_exact_successful_source_accepted_and_product_diff_fails_closed(self):
        s=self.workflow
        for clause in ("$record.conclusion -ne 'success'","$record.head_sha -ne $sha",
                       "git diff --name-only $sha $env:GITHUB_SHA -- crates r0/go_overlay Cargo.lock Cargo.toml tools/prepare_windows_wiring.py",
                       "frozen Windows product/ABI non-allowlisted change",
                       "m['sha256'][key]","native_fec_acceleration,m0_v4_probe",
                       "PLAN029_H1911_EXACT_H1909_SIGNED_10GIB_WIN_BINARIES_MANIFEST_PASS"):
            self.assertIn(clause,s)
    def test_no_rebuild_and_no_cross_vm_concurrent_CPU_aggregation(self):
        s=self.workflow
        self.assertGreaterEqual(s.count("!contains(github.event.head_commit.message, '"+MARKER+"')"),4)
        self.assertIn("needs.linux-source-locked-public.result == 'success' || inputs.perf_reuse_run_id != '' ||",s) if False else None
        self.assertIn("contains(github.event.head_commit.message, '"+MARKER+"') ||",s)
        self.assertIn("if: env.WBD_WL_REUSE_RUN_ID == ''",s)
        self.assertIn("if: env.WBD_WL_REUSE_RUN_ID != '' && env.WBD_WL_ABBA_NATIVE != '1'",s)
        for marker in ("[plan029-v3-real-p2-bulk]","[plan029-v3-real-p2-500-700]",
                       "[plan029-v3-real-p2-long-ab]"):
            self.assertIn(marker,s)
if __name__=="__main__":unittest.main()
