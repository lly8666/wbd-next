"""H2278: original 1%/5% Windows cold OFF→ON TCP evidence is per leg."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from m0_wl_loss_tcp_probe import archive_loss_tcp_stage


class RealColdLegArchive(unittest.TestCase):
    def test_windows_and_linux_stage_move_preserves_original_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            out=pathlib.Path(root)
            leg=out/"outer-pair"/"off"
            leg.mkdir(parents=True)
            for origin in ("windows","linux"):
                d=out/("m029-h2271-"+origin)
                d.mkdir()
                (d/"server.log").write_bytes(("server-"+origin).encode())
                (d/"client.log").write_bytes(("client-"+origin).encode())
            moved=archive_loss_tcp_stage(out,leg)
            self.assertEqual(moved,["windows","linux"])
            for origin in moved:
                self.assertFalse((out/("m029-h2271-"+origin)).exists())
                d=leg/("m029-h2271-"+origin)
                self.assertEqual((d/"server.log").read_bytes(),
                                 ("server-"+origin).encode())
                self.assertEqual((d/"client.log").read_bytes(),
                                 ("client-"+origin).encode())
            newleg=out/"outer-pair"/"on"
            newleg.mkdir()
            for origin in moved:
                (out/("m029-h2271-"+origin)).mkdir()
            self.assertEqual(archive_loss_tcp_stage(out,newleg),moved)
            self.assertTrue((leg/"m029-h2271-windows"/"server.log").exists())

    def test_prior_target_must_not_be_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            out=pathlib.Path(root)
            leg=out/"outer-pair"/"on"
            leg.mkdir(parents=True)
            (out/"m029-h2271-windows").mkdir()
            (leg/"m029-h2271-windows").mkdir()
            with self.assertRaisesRegex(RuntimeError,"H2278_TCP_ARCHIVE"):
                archive_loss_tcp_stage(out,leg)
            self.assertTrue((out/"m029-h2271-windows").exists())

    def test_wrong_file_type_is_not_moved(self):
        with tempfile.TemporaryDirectory() as root:
            out=pathlib.Path(root)
            leg=out/"outer-pair"/"on"
            leg.mkdir(parents=True)
            (out/"m029-h2271-windows").write_text("not an origin directory")
            with self.assertRaisesRegex(RuntimeError,"H2278_TCP_ARCHIVE"):
                archive_loss_tcp_stage(out,leg)

    def test_missing_stages_stay_unknown_not_fabricated(self):
        with tempfile.TemporaryDirectory() as root:
            out=pathlib.Path(root)
            leg=out/"outer-pair"/"off"
            leg.mkdir(parents=True)
            self.assertEqual(archive_loss_tcp_stage(out,leg),[])


if __name__=="__main__":
    unittest.main()
