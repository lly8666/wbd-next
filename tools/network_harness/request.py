"""Materialize ONE preset into a reviewable request; never dispatch a matrix."""
import argparse
import json
from pathlib import Path
from .config import validate

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("scenario")
    p.add_argument("--base", default="tests/network/request.json")
    p.add_argument("--output", required=True)
    p.add_argument("--catalog", default="tests/network/scenarios.json")
    a = p.parse_args()
    request = json.loads(Path(a.base).read_text())
    case = json.loads(Path(a.catalog).read_text())[a.scenario]
    request.update(case)
    request["id"] = a.scenario
    # These are explicit observation presets, not arbitrary zero-loss assertions.
    if "acceptance" not in case:
        request["acceptance"] = {"injection_tolerance_pct": 3}
    Path(a.output).write_text(json.dumps(validate(request), indent=2) + "\n")
