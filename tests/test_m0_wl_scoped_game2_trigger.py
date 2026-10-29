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

if __name__=="__main__":unittest.main()
