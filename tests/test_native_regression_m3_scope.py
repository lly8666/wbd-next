"""M0 source-locked separate R1 codec and M3 F2 qualification boundaries."""
import unittest
from tools import native_regression as n
class Tests(unittest.TestCase):
    def test_r1_codec_mandatory_cases_unskipped_and_f2_separately_qualified(self):
        c=n.suites()["codec"]
        self.assertEqual(n.native_group_selection("codec",c),[
            "r1_","--skip","r1_f2_","--skip",
            "r1_steady_release_same_source_fresh_vs_reused_owner_cost"])
        # Only the unbounded CPU comparison is excluded from the functional
        # gate; no mandatory codec assertion can be silently skipped.
        self.assertFalse("r1_steady_release_same_source_fresh_vs_reused_owner_cost" in c["required"])
        self.assertTrue(all(required not in
            n.native_group_selection("codec",c)[2::2] for required in c["required"]))
        self.assertTrue(c["required"])
        self.assertFalse(any(x.startswith("r1_f2_") for x in c["required"]))
    def test_future_mandatory_f2_cannot_be_skipped(self):
        c=dict(n.suites()["codec"])
        c["required"]=c["required"]+["r1_f2_native_decode_tables_and_workspace_reused_dirty_tail_exact"]
        with self.assertRaisesRegex(ValueError,"cannot skip mandatory F2"):
            n.native_group_selection("codec",c)
    def test_other_groups_keep_original_full_selection(self):
        for role,spec in n.suites().items():
            if role!="codec":
                self.assertEqual(n.native_group_selection(role,spec),
                                 [spec["filter"]] if spec["filter"] else [])
if __name__=="__main__":unittest.main()
