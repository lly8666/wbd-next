"""Adversarial one-page G2 activation ancestry checks."""
import unittest
from tools import worker_scope_ci as w
from tools import governance as g

def example(n,actual=None,status="ahead"):
    m=n if actual is None else actual
    return {"total_commits":n,"status":status,
            "commits":[{"sha":f"{i:040x}"} for i in range(m)]}

class BoundedG2(unittest.TestCase):
    def test_exact_old_limit(self):self.assertEqual(len(w.complete_g2_ancestry(example(64))),64)
    def test_actual_new_67(self):self.assertEqual(len(w.complete_g2_ancestry(example(67))),67)
    def test_max_96(self):self.assertEqual(len(w.complete_g2_ancestry(example(96))),96)
    def test_max_98(self):self.assertEqual(len(w.complete_g2_ancestry(example(98))),98)
    def test_too_many_99(self):
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(example(99))
    def test_full_98_not_97(self):
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(example(98,97))
    def test_page_truncation(self):
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(example(67,64))
    def test_diverged(self):
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(example(67,status="diverged"))
    def test_behind(self):
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(example(67,status="behind"))
    def test_duplicate(self):
        x=example(67);x["commits"][2]["sha"]=x["commits"][0]["sha"]
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(x)
    def test_invalid_sha(self):
        x=example(67);x["commits"][0]["sha"]="invalid"
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(x)
    def test_negative(self):
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(example(-1,0))
if __name__=="__main__":unittest.main()
