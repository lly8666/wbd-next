"""Ensure explicit Game2 trial cannot fan out to seven real native Windows modes."""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
class Game2ScopedWindowsLaunchTests(unittest.TestCase):
    def test_both_preflight_and_native_job_pick_game2_before_other_modes(self):
        y=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        trigger="[plan026-game2-only]"
        for name in ("PUBLIC_MODE","WBD_WL_PUBLIC_MODES"):
            row=next(x.strip() for x in y.splitlines() if x.strip().startswith(name+":"))
            self.assertIn(trigger,row)
            self.assertIn("&& 'game2' ||",row)
            self.assertLess(row.index(trigger),row.index("inputs.public_mode"))
        self.assertIn("WL_WSL2_OUTER_WATCHDOG_ARMED",y)
        self.assertIn("timeout-minutes: 24",y)

    def test_original_prompt_failing_game2_order_is_preserved(self):
        from tools.m0_wl_mode_evidence import select_source_locked_modes
        self.assertEqual(select_source_locked_modes("through-game2"),
                         ["normal","fixed","auto","game2"])
        with self.assertRaises(ValueError):
            select_source_locked_modes("through-game2",performance=True)
        y=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        for name in ("PUBLIC_MODE","WBD_WL_PUBLIC_MODES"):
            row=next(x.strip() for x in y.splitlines() if x.strip().startswith(name+":"))
            self.assertIn("[plan026-game2-historical-order]",row)
            self.assertIn("&& 'through-game2' ||",row)
        self.assertIn("Copy-Item result/wl-public/game2-report.json",y)
        self.assertIn("m0_wl_native_step_runner.py",y)

if __name__=="__main__":unittest.main()
