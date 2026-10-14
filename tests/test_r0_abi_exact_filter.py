"""Unit-check exact native Rust ABI output selector; Actions executes real ABI."""
import importlib.util
import pathlib
import unittest

p = pathlib.Path(__file__).resolve().parents[1] / "tools" / "r0_abi_bundle.py"
spec = importlib.util.spec_from_file_location("r0_abi_bundle", p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

CASES = tuple(sorted(module.RUST_ABI_CASES))

def output(names=CASES, passed=3, failed=0):
    lines = [f"test tests::{name} ... ok" for name in names]
    lines.append(f"test result: ok. {passed} passed; {failed} failed; 0 ignored; 0 measured; 19 filtered out; finished in 0.00s")
    return "\n".join(lines)

class ExactAbiSelection(unittest.TestCase):
    def test_exact_three_abi_pass(self):
        module.verify_three_rust_abi_cases(output())
    def test_unfiltered_13_pass_substring_trap(self):
        with self.assertRaises(ValueError):
            module.verify_three_rust_abi_cases(output(passed=13))
    def test_unfiltered_22_pass_with_three_abi_names_not_accepted(self):
        with self.assertRaises(ValueError):
            module.verify_three_rust_abi_cases(output(passed=22))
    def test_missing_abi_case_rejected(self):
        with self.assertRaises(ValueError):
            module.verify_three_rust_abi_cases(output(names=CASES[:2]))
    def test_extra_or_duplicated_abi_case_rejected(self):
        with self.assertRaises(ValueError):
            module.verify_three_rust_abi_cases(output(names=CASES + (CASES[0],)))
    def test_wrong_name_rejected(self):
        with self.assertRaises(ValueError):
            module.verify_three_rust_abi_cases(output(names=CASES[:2] + ("r0_abi_unknown",)))
    def test_failed_count_rejected(self):
        with self.assertRaises(ValueError):
            module.verify_three_rust_abi_cases(output(passed=3,failed=1))
    def test_accept_realistic_qualified_output(self):
        module.verify_three_rust_abi_cases("\n".join([
            "running 3 tests", *[f"test tests::{v} ... ok" for v in CASES],
            "test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 19 filtered out; finished in 0.00s",]))
if __name__ == "__main__":
    unittest.main()
