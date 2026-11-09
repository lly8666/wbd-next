import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("h1459",ROOT/"tools/m0_plan028_h1459_offline_rejudge.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
class H1459OfflineVerdictTests(unittest.TestCase):
    def test_zero_loss_one_true_queue_overflow_must_not_be_pass(self):
        self.assertTrue(mod.classify_zero_loss(0,5,"PASS_SCOPED",True).startswith("FAIL_SCOPED"))
        self.assertTrue(mod.classify_zero_loss(28,0,"PASS_SCOPED",True).startswith("FAIL_SCOPED"))
    def test_zero_loss_clean_retains_scoped_pass(self):
        self.assertEqual(mod.classify_zero_loss(0,0,"PASS_SCOPED",True),"PASS_SCOPED")
    def test_capacity_limit_or_bad_business_cannot_be_promoted(self):
        self.assertEqual(mod.classify_zero_loss(0,0,"CAPACITY_LIMITED_OR_GENERATOR_LIMITED",True),
                         "CAPACITY_LIMITED_OR_GENERATOR_LIMITED")
        self.assertTrue(mod.classify_zero_loss(0,0,"PASS_SCOPED",False).startswith("FAIL_"))
    def test_stale_historical_enum_is_still_visible_not_silently_fixed(self):
        s=(ROOT/".github/workflows/m0-plan028-h1349-x86-game4-fixed6-zero-loss-capacity.yml").read_text()
        self.assertIn("PASS_SCOPED_0LOSS_GAME4_FIXED6_3_5_10_5_WITH_FIVE_SIBLINGS",s)
if __name__=="__main__":
    unittest.main()
