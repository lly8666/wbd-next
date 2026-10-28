"""Historical receipts cannot gain qualifications when the live project advances."""
import copy
import json
from pathlib import Path
import unittest

from tools.r0_qualification_audit import audit_historical_qualification


class HistoricalQualificationTests(unittest.TestCase):
    def test_original_receipt_and_every_promotion_boundary(self):
        lock = json.loads(Path("r0/source-lock.json").read_text())
        audit_historical_qualification(lock)
        changed = copy.deepcopy(lock)
        changed["phase"] = "MAIN_PRODUCT_STABILITY_AND_NETWORK_CLOSEOUT"
        with self.assertRaises(ValueError):
            audit_historical_qualification(changed)
        for key in ("product", "performance", "physical",
                    "windows_arm_native_execution", "rust_business_engine"):
            with self.subTest(key=key):
                changed = copy.deepcopy(lock)
                changed["qualification"][key] = "PASS"
                with self.assertRaises(ValueError):
                    audit_historical_qualification(changed)
