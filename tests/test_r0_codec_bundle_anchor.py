"""M0 R0 WBC4/WBG4 wire anchors still strict when M3 registers native tests."""
import unittest
from tools import r0_codec_bundle as c

def rustlog(anchors=c.TESTS,extra=(),summary=None,failed=()):
    rows=[f"test tests::{x} ... ok" for x in anchors]
    rows += [f"test fec_v2::fec_v2_tests::{x} ... ok" for x in extra]
    rows += [f"test fec_v2::fec_v2_tests::{x} ... FAILED" for x in failed]
    total=(len(anchors)+len(extra)) if summary is None else summary
    rows.append(f"test result: ok. {total} passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.00s")
    return "\n".join(rows)+"\n"
class Tests(unittest.TestCase):
    def test_exact_wire_13_plus_native_10_are_valid(self):
        s=rustlog(extra=[f"r1_f2_verified_{i}" for i in range(10)])
        anchors,failed,valid,total=c.validate_wire_anchors(s,0)
        self.assertTrue(valid)
        self.assertEqual(len(anchors),13)
        self.assertEqual(total,23)
        self.assertEqual(failed,[])
    def test_reject_missing_duplicate_failure_and_lied_total(self):
        samples=[
            rustlog(anchors=c.TESTS[:-1]),
            rustlog(anchors=c.TESTS+(c.TESTS[0],)),
            rustlog(extra=["native_0"],summary=13),
            rustlog(extra=["native_0"],failed=["native_err"]),
            rustlog(extra=["native_0"]).replace("0 failed","1 failed"),
            rustlog(extra=["native_0"]).replace("test result: ok.","test result: FAILED."),
        ]
        for i,s in enumerate(samples):
            with self.subTest(i=i):self.assertFalse(c.validate_wire_anchors(s,0)[2])
        self.assertFalse(c.validate_wire_anchors(rustlog(),1)[2])
    def test_fec_fixtures_never_count_as_wire_anchors(self):
        self.assertFalse(c.validate_wire_anchors(rustlog(anchors=(),extra=c.TESTS),0)[2])
if __name__=="__main__":unittest.main()
