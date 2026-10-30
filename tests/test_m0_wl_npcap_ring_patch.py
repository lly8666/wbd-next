"""Pinned Windows Npcap source-size patch is deterministic and fail closed."""
import pathlib
import unittest
from tools import prepare_windows_wiring as a

ROOT=pathlib.Path(__file__).resolve().parents[1]
class WindowsNpcapRingTests(unittest.TestCase):
 def test_source_patch_requires_exact_unique_original_anchor(self):
  self.assertEqual(a.replace_original_once(b'one and two',b'two',b'changed','a'),b'one and changed')
  with self.assertRaisesRegex(ValueError,"anchor changed"):
   a.replace_original_once(b'two two',b'two',b'changed','a')
  with self.assertRaisesRegex(ValueError,"anchor changed"):
   a.replace_original_once(b'one',b'two',b'changed','a')
 def test_kernel_capture_before_mintocopy_after_open_no_online_reset(self):
  s=(ROOT/"tools/prepare_windows_wiring.py").read_text()
  self.assertIn("pcap_setbuff",s)
  self.assertIn("16 << 20",s)
  self.assertIn("captureBytes := cfg.CaptureBufferBytes",s)
  self.assertIn("result_blob",s)
  self.assertIn("original Npcap source changed",s)
  self.assertIn('win_after = replace_original_once(win_before, marker, injection + marker',s)
  overlay=(ROOT/"r0/go_overlay/internal/faketcp/npcap_native_handoff_windows.go").read_text()
  self.assertIn("return e.cfg,nil",overlay)
  self.assertNotIn("CaptureBufferBytes",overlay)
  self.assertIn("cfg.CaptureBufferBytes=1<<20",s)
  self.assertIn('clone_after=original_clone.replace(old_return,new_return)',s)
 def test_assembly_blob_matches_real_git_sha(self):
  import json,hashlib
  p=ROOT/"r0/go_overlay/internal/faketcp/npcap_native_handoff_windows.go"
  b=p.read_bytes()
  digest=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
  spec=json.loads((ROOT/"r0/go_overlay/assembly/manifest-plan020-m0.json").read_text())
  ops=[o for o in spec["operations"] if o.get("overlay_path")=="r0/go_overlay/internal/faketcp/npcap_native_handoff_windows.go"]
  self.assertEqual(len(ops),1)
  self.assertEqual(ops[0]["result_blob"],digest)

if __name__=="__main__":unittest.main()
