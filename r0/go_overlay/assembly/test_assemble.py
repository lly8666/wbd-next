"""Deterministic source-lock/create/replace smoke without network or privileged OS."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from assemble import assemble, blob_sha


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name)
        self.legacy=base/"legacy"
        self.overlay=base/"overlay"
        self.legacy.mkdir()
        self.overlay.mkdir()
        for root in (self.legacy,self.overlay):
            subprocess.run(["git","-C",str(root),"init","-q"],check=True)
            subprocess.run(["git","-C",str(root),"config","user.email","test@example.invalid"],check=True)
            subprocess.run(["git","-C",str(root),"config","user.name","test"],check=True)
        (self.legacy/"cmd").mkdir()
        (self.legacy/"cmd/original.go").write_bytes(b"package main\n// OLD\n")
        (self.overlay/"r0").mkdir()
        (self.overlay/"r0/source-lock.json").write_text("{}\n")
        (self.overlay/"r0/policy.go").write_bytes(b"package main\n")
        for root in (self.legacy,self.overlay):
            subprocess.run(["git","-C",str(root),"add","."],check=True)
            subprocess.run(["git","-C",str(root),"commit","-qm","pin"],check=True)
        self.old=(self.legacy/"cmd/original.go").read_bytes()
        self.spec={
            "schema_version":1,
            "legacy_source":subprocess.check_output(["git","-C",str(self.legacy),"rev-parse","HEAD"],text=True).strip(),
            "rust_source":"0"*40,
            "operations":[
                {"kind":"replace","path":"cmd/original.go",
                 "original_blob":blob_sha(self.old),
                 "result_blob":blob_sha(b"package main\n// NEW\n"),
                 "patches":[{"find":"// OLD","replace":"// NEW"}]},
                {"kind":"create","path":"cmd/policy.go",
                 "overlay_path":"r0/policy.go",
                 "result_blob":blob_sha(b"package main\n")}
            ],
        }
        self.manifest=Path(self.temp.name)/"manifest.json"
        self.receipt=Path(self.temp.name)/"result.json"
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.spec),encoding="utf-8")

    def test_dry_run_preflight_and_atomic_overlays(self):
        assemble(self.legacy,self.overlay,self.manifest,self.receipt,True)
        self.assertEqual((self.legacy/"cmd/original.go").read_bytes(),self.old)
        self.assertFalse((self.legacy/"cmd/policy.go").exists())
        assemble(self.legacy,self.overlay,self.manifest,self.receipt,False)
        self.assertEqual((self.legacy/"cmd/original.go").read_bytes(),b"package main\n// NEW\n")
        self.assertEqual((self.legacy/"cmd/policy.go").read_bytes(),b"package main\n")
        self.assertEqual(json.loads(self.receipt.read_text())["result"],"APPLIED_TO_PINNED_TEMP_CLONE")
        with self.assertRaises(ValueError):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,False) # no silent overwrite

    def test_fail_before_any_write_on_original_blob_drift(self):
        self.spec["operations"][0]["original_blob"]="0"*40
        self.save()
        with self.assertRaisesRegex(ValueError,"original blob mismatch"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,False)
        self.assertEqual((self.legacy/"cmd/original.go").read_bytes(),self.old)

    def test_fail_before_write_on_result_sha_or_nonunique_anchor(self):
        self.spec["operations"][1]["result_blob"]="0"*40
        self.save()
        with self.assertRaisesRegex(ValueError,"overlay result blob"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,False)
        self.assertFalse((self.legacy/"cmd/policy.go").exists())
        self.spec["operations"][1]["result_blob"]=blob_sha(b"package main\n")
        self.spec["operations"][0]["patches"][0]["find"]="// ABSENT"
        self.save()
        with self.assertRaisesRegex(ValueError,"non-exact replacement"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,False)
        self.assertEqual((self.legacy/"cmd/original.go").read_bytes(),self.old)

    def test_duplicate_and_path_traversal_rejected(self):
        self.spec["operations"][1]["path"]="cmd/original.go"
        self.save()
        with self.assertRaisesRegex(ValueError,"duplicate assembly target"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,True)
        self.spec["operations"][1]["path"]="../outside.go"
        self.save()
        with self.assertRaisesRegex(ValueError,"invalid relative"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,True)

    def with_twelve_exact_windows_donor_files(self):
        self.spec["windows_donor_source"] = "6"*40
        for i in range(12):
            name = f"native_pin_{i:02d}_windows.go"
            path = "internal/windowsclient/" + name
            opath = "r0/go_overlay/" + path
            source = self.overlay / opath
            source.parent.mkdir(parents=True,exist_ok=True)
            content = f"package windowsclient\\n// DONOR-{i}\\n".encode()
            source.write_bytes(content)
            entry = dict(kind="replace" if i<8 else "create",path=path,
                         overlay_path=opath,donor_source="6"*40,
                         donor_blob=blob_sha(content),result_blob=blob_sha(content))
            if i<8:
                original = self.legacy / path
                original.parent.mkdir(parents=True,exist_ok=True)
                baseline = f"package windowsclient\\n// BASE-{i}\\n".encode()
                original.write_bytes(baseline)
                entry["original_blob"] = blob_sha(baseline)
            self.spec["operations"].append(entry)
        self.save()

    def test_complete_exact_donor_batch_replaces_and_creates(self):
        self.with_twelve_exact_windows_donor_files()
        assemble(self.legacy,self.overlay,self.manifest,self.receipt,True)
        self.assertFalse((self.legacy/"internal/windowsclient/native_pin_11_windows.go").exists())
        assemble(self.legacy,self.overlay,self.manifest,self.receipt,False)
        outcome=json.loads(self.receipt.read_text())
        self.assertEqual(outcome["donor_file_count"],12)
        self.assertEqual(outcome["windows_donor_source"],"6"*40)
        for i in range(12):
            self.assertIn(f"DONOR-{i}",(self.legacy/f"internal/windowsclient/native_pin_{i:02d}_windows.go").read_text())

    def test_donor_tamper_wrong_base_wrong_source_and_batch_fail_closed(self):
        self.with_twelve_exact_windows_donor_files()
        entry=self.spec["operations"][-1]
        f=self.overlay/entry["overlay_path"]
        f.write_text("package windowsclient\\n// malicious\\n")
        self.save()
        with self.assertRaisesRegex(ValueError,"donor blob mismatch"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,False)
        self.assertFalse((self.legacy/entry["path"]).exists())
        f.write_text("package windowsclient\\n// DONOR-11\\n")
        original=self.spec["operations"][2]
        original["original_blob"]="0"*40
        self.save()
        with self.assertRaisesRegex(ValueError,"original blob mismatch"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,False)
        original["original_blob"]=blob_sha((self.legacy/original["path"]).read_bytes())
        entry["donor_source"]="f"*40
        self.save()
        with self.assertRaisesRegex(ValueError,"paths/source"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,False)
        entry["donor_source"]="6"*40
        self.spec["operations"].pop()
        self.save()
        with self.assertRaisesRegex(ValueError,"12-file batch"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,False)

    def test_fail_if_checkout_source_drifted(self):
        self.spec["legacy_source"]="0"*40
        self.save()
        with self.assertRaisesRegex(ValueError,"SOURCE not pinned"):
            assemble(self.legacy,self.overlay,self.manifest,self.receipt,True)


if __name__=="__main__":
    unittest.main()
