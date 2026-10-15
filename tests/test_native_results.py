import unittest
from tools.native_results import rust_results, go_results


def log(names=("suite::essential",), ignored=()):
    return "\n".join([*(f"test {n} ... ok" for n in names),
                      *(f"test {n} ... ignored" for n in ignored),
                      f"test result: ok. {len(names)} passed; 0 failed; {len(ignored)} ignored; 0 measured; 0 filtered out;"])


class NativeResults(unittest.TestCase):
    def test_added_cases_do_not_change_contract(self):
        for n in (0, 1, 100):
            self.assertEqual(rust_results(log(("suite::essential", *(f"suite::new{i}" for i in range(n)))), 0,
                                          ["essential"])["result"], "PASS")

    def test_omission_duplicate_ambiguous_and_nonzero_fail(self):
        for names, code in [((), 0), (("other",), 0), (("essential", "essential"), 0),
                            (("a::essential", "b::essential"), 0), (("essential",), 1)]:
            self.assertEqual(rust_results(log(names), code, ["essential"])["result"], "FAIL")

    def test_ignored_cannot_hide_required_case(self):
        self.assertEqual(rust_results(log(("other",), ("essential",)), 0,
                                     ["essential"], ["essential"])["result"], "FAIL")

    def test_only_declared_benchmark_ignore(self):
        self.assertEqual(rust_results(log(ignored=("bench",)), 0, ["essential"], ["bench"])["result"], "PASS")
        self.assertEqual(rust_results(log(ignored=("new_missing",)), 0, ["essential"], ["bench"])["result"], "FAIL")

    def test_missing_truncated_multiple_or_invented_summary(self):
        valid = log()
        for text in ("", valid.split("test result:")[0], valid + "\n" + valid,
                     valid.replace("1 passed", "2 passed"), valid.replace("0 failed", "1 failed")):
            self.assertEqual(rust_results(text, 0, ["essential"])["result"], "FAIL")

    def test_go_required_named_cases_and_growth(self):
        log = '--- PASS: TestEssential (0.01s)\n--- PASS: TestExtra (0.00s)\nPASS\n'
        self.assertEqual(go_results(log, 0, ['TestEssential'])["result"], 'PASS')
        for bad, code in [(log.replace('PASS: TestEssential', 'SKIP: TestEssential'), 0),
                          (log, 1), (log.replace('TestEssential', 'TestOther'), 0),
                          ('    --- PASS: TestEssential (0s)\nPASS\n', 0)]:
            self.assertEqual(go_results(bad, code, ['TestEssential'])["result"], 'FAIL')
