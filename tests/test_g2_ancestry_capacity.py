"""Fail-closed, bounded MULTI-PAGE G2 immutable ancestry assertions."""
import unittest
from tools import worker_scope_ci as w
from tools import governance as g

B=w.G2_BASE
HEAD="f"*40
SIZE=w.G2_ACTIVATION_PAGE_SIZE

def entry(n):
    return {"sha":f"{n:040x}"}

def example(n,actual=None,status="ahead"):
    m=n if actual is None else actual
    return {"total_commits":n,"status":status,
            "commits":[entry(i) for i in range(m)]}

class Mock:
    def __init__(self,n,pages=None,partial=None,status="ahead",head=HEAD,
                 changed_total=None,missing_page=None):
        self.n=n;self.head=head;self.changed_total=changed_total
        self.status=status;self.missing_page=missing_page
        self.commits=[entry(i) for i in range(max(0,n-1))]+([{"sha":head}] if n else [])
        self.pages=pages or {}
        self.partial=partial
        self.calls=[]
    def get(self,query):
        self.calls.append(query)
        prefix=f"compare/{B}...{self.head}?per_page={SIZE}&page="
        if not query.startswith(prefix):
            raise AssertionError(query)
        page=int(query.split("page=",1)[1])
        if page==self.missing_page:
            return {"status":self.status,"total_commits":self.n,"commits":[]}
        sl=self.commits[(page-1)*SIZE:page*SIZE]
        return {"status":self.status,
                "total_commits":self.changed_total if page==2 else self.n,
                "commits":self.pages.get(page,sl),
                "behind_by":0,"ahead_by":self.n}

class BoundedG2(unittest.TestCase):
    def test_old_one_page_limits_are_still_complete(self):
        for n in (1,64,67,96,98,99):
            self.assertEqual(len(w.complete_g2_ancestry(example(n))),n)
    def test_multpage_100_180_and_512_complete(self):
        for n in (100,180,512):
            a=Mock(n)
            self.assertEqual(len(w.fetch_complete_g2_ancestry(a,HEAD)),n)
            self.assertEqual(len(a.calls),(n+SIZE-1)//SIZE)
    def test_over_budget_513(self):
        with self.assertRaises(g.ContractError):
            w.fetch_complete_g2_ancestry(Mock(513),HEAD)
    def test_missing_middle_page(self):
        with self.assertRaises(g.ContractError):
            w.fetch_complete_g2_ancestry(Mock(180,missing_page=2),HEAD)
    def test_cross_snapshot_total_changed(self):
        with self.assertRaises(g.ContractError):
            w.fetch_complete_g2_ancestry(Mock(180,changed_total=179),HEAD)
    def test_duplicate_page(self):
        m=Mock(180)
        first=m.commits[:SIZE]
        with self.assertRaises(g.ContractError):
            w.fetch_complete_g2_ancestry(Mock(180,pages={2:first}),HEAD)
    def test_final_page_does_not_end_at_frozen_source(self):
        with self.assertRaises(g.ContractError):
            w.fetch_complete_g2_ancestry(Mock(180,pages={3:[entry(179)]}),HEAD)
    def test_missing_tail(self):
        with self.assertRaises(g.ContractError):
            w.fetch_complete_g2_ancestry(Mock(100,pages={2:[]}),HEAD)
    def test_page_truncation(self):
        with self.assertRaises(g.ContractError):
            w.complete_g2_ancestry(example(99,98))
    def test_diverged_and_behind(self):
        for status in ("diverged","behind"):
            with self.assertRaises(g.ContractError):
                w.fetch_complete_g2_ancestry(Mock(100,status=status),HEAD)
    def test_duplicate(self):
        x=example(67);x["commits"][2]["sha"]=x["commits"][0]["sha"]
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(x)
    def test_invalid_sha(self):
        x=example(67);x["commits"][0]["sha"]="invalid"
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(x)
    def test_negative(self):
        with self.assertRaises(g.ContractError):w.complete_g2_ancestry(example(-1,0))

if __name__=="__main__":unittest.main()
