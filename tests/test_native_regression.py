import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import native_regression as n


class NativePlan(unittest.TestCase):
    def test_docs_select_none_root_selects_all_leaf_selects_dependents(self):
        specs = n.suites()
        self.assertEqual(n.affected(['docs/devlog/M0/new.md'], specs), [])
        self.assertEqual(n.affected(['Cargo.lock'], specs), sorted(specs))
        groups = n.affected(['crates/wbd-codec/src/fec_rx.rs'], specs)
        self.assertEqual(groups, sorted(['codec', 'engine', 'normal', 'fec', 'kernel', 'receipt']))
        self.assertEqual(n.affected(['crates/wbd-engine/src/runtime/mod.rs'], specs),
                         sorted(['engine', 'normal', 'fec', 'kernel', 'receipt']))

    def test_required_inventory_is_nonempty_and_has_no_duplicates(self):
        for name, spec in n.suites().items():
            self.assertTrue(spec['required'], name)
            self.assertEqual(len(spec['required']), len(set(spec['required'])), name)
            self.assertFalse(set(spec['required']) & set(spec['allowed_ignored']), name)

    def test_wrong_source_attempt_flags_bytes_or_input_rejected(self):
        env={'GITHUB_SHA':'a'*40,'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1',
             'RUNNER_OS':'Linux','RUNNER_ARCH':'X64','RUSTFLAGS':''}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, env), \
             patch.object(n, 'BUILD', Path(temp)), patch.object(n, 'inputs', return_value={'source.rs':'hash'}):
            binary=Path(temp)/'codec.test'; binary.write_bytes(b'binary')
            good={'source_sha':'a'*40,'run_id':'123','attempt':'1','target':'x86_64-unknown-linux-gnu',
                  'rust':n.RUST,'profile':'release','features':'default','rustflags':'',
                  'inputs':{'source.rs':'hash'},
                  'binaries':{'codec':{'name':'codec.test','bytes':6,'sha256':n.digest(binary)}}}
            self.assertEqual(n.verify(good, 'codec'), binary)
            for key,value in [('source_sha','b'*40),('attempt','2'),('rustflags','-C target-cpu=native'),
                              ('inputs',{}),('target','aarch64-unknown-linux-gnu')]:
                bad=copy.deepcopy(good);bad[key]=value
                with self.subTest(key=key), self.assertRaises(ValueError): n.verify(bad,'codec')
            binary.write_bytes(b'changed')
            with self.assertRaises(ValueError): n.verify(good,'codec')
