"""Parse complete libtest results; additions are allowed, omissions are not.

Run the binary with --test-threads=1 so its outcome lines are unambiguous.
Required names use full Rust paths. Explicit suffixes are accepted only when
they match exactly one outcome. Unexpected ignored tests always fail.
"""
import re


def rust_results(log, exit_code, required=(), allowed_ignored=()):
    outcomes = re.findall(r"^test ([\w:]+) \.\.\. (ok|FAILED|ignored)(?:, [^\n]*)?$", log, re.M)
    summaries = re.findall(r"^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;", log, re.M)
    names = [name for name, _ in outcomes]
    passed = [name for name, state in outcomes if state == "ok"]
    ignored = [name for name, state in outcomes if state == "ignored"]

    def matches(name, candidates):
        return [n for n in candidates if n == name or n.endswith("::" + name)]

    missing = [n for n in required if len(matches(n, passed)) != 1]
    unexpected = [n for n in ignored if not any(n == a or n.endswith("::" + a) for a in allowed_ignored)]
    valid = (exit_code == 0 and len(summaries) == 1 and bool(passed)
             and len(names) == len(set(names)) and not missing and not unexpected)
    if len(summaries) == 1:
        state, n_pass, n_fail, n_ignore = summaries[0]
        valid = valid and state == "ok" and int(n_fail) == 0 and not any(s == "FAILED" for _, s in outcomes)
        valid = valid and int(n_pass) == len(passed) and int(n_ignore) == len(ignored)
    return {"result": "PASS" if valid else "FAIL", "passed": passed, "ignored": ignored,
            "missing_required": missing, "unexpected_ignored": unexpected, "exit_code": exit_code}


def go_results(log, exit_code, required):
    outcomes = re.findall(r"^--- (PASS|FAIL|SKIP): (Test\w+)(?: \([^\n]*\))?$", log, re.M)
    names = [name for _, name in outcomes]
    passed = [name for state, name in outcomes if state == "PASS"]
    valid = (exit_code == 0 and bool(passed) and len(names) == len(set(names))
             and all(state == "PASS" for state, _ in outcomes)
             and set(required) <= set(passed) and len(re.findall(r"^PASS$", log, re.M)) == 1)
    return {"result": "PASS" if valid else "FAIL", "passed": passed,
            "missing_required": sorted(set(required) - set(passed)), "exit_code": exit_code}
