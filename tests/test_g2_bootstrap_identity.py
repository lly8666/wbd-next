"""Source-locked G2 authority gate must distinguish live rev3 from frozen M4."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("g2_bootstrap_bundle", ROOT/"tools/g2_bootstrap_bundle.py")
g2=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g2)

class G2IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old=os.getcwd()
        os.chdir(self.temp.name)
        self.p=Path(self.temp.name)
        self.registry={"reservation_revision":3,"roles":[
            {"id":"M0","state":"active","branch":"main","assignment_epoch":1,"global_writer":True},
            *[{"id":x,"state":"active","assignment_epoch":1,"global_writer":False} for x in ("M1","M2","M3")],
            {"id":"M4","state":"reserved","assignment_epoch":2,"allowed_paths":[],"owned_semantics":[]},
        ]}
        for role in self.registry["roles"]:
            p=self.p/f".governance/workstreams/{role['id']}/cursor.json"
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps({"role_id":role["id"],"assignment_epoch":1,
                  "reservation_revision":2 if role["id"]!="M0" else 3}))
        lock=self.p/"r0/source-lock.json"
        lock.parent.mkdir(parents=True)
        lock.write_text(json.dumps({"rust":{"crates":list(
              ("wbd-types","wbd-codec","wbd-engine","wbd-platform","wbd-recovery"))}}))
        self.save()
        self.env=mock.patch.dict(os.environ,{"RUNNER_OS":"Linux","RUNNER_ARCH":"X64"})
        self.env.start()
    def tearDown(self):
        self.env.stop()
        os.chdir(self.old)
        self.temp.cleanup()
    def save(self):
        (self.p/".governance/registry.json").write_text(json.dumps(self.registry))
    def test_rev3_active_three_and_frozen_m4_accepted(self):
        g2.identity()
    def test_m4_old_active_lease_rejected(self):
        m4=self.registry["roles"][-1]
        m4.update(state="active",assignment_epoch=1)
        self.save()
        with self.assertRaisesRegex(ValueError,"M4 revoked lease"):
            g2.identity()
    def test_rev2_control_rejected(self):
        self.registry["reservation_revision"]=2
        self.save()
        with self.assertRaisesRegex(ValueError,"G2 registry revision"):
            g2.identity()
    def test_main_worker_snapshot_future_revision_rejected(self):
        p=self.p/".governance/workstreams/M2/cursor.json"
        d=json.loads(p.read_text());d["reservation_revision"]=4;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,"active cursor snapshot"):
            g2.identity()
    def test_frozen_m4_cursor_rewrite_rejected(self):
        p=self.p/".governance/workstreams/M4/cursor.json"
        d=json.loads(p.read_text());d["assignment_epoch"]=2;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,"M4 historic cursor"):
            g2.identity()

if __name__=="__main__":
    unittest.main()
