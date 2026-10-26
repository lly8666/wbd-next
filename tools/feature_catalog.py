"""Product feature inventory and change gate; no network or product execution.

The catalog describes product behavior, not writer authority. CI checks shape
and explicit change declarations; humans still verify semantic completeness.
"""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CATALOG = "docs/features/entries/"
STATE = "docs/features/inventory.json"
SHA = re.compile(r"[0-9a-f]{40}")
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
STATUSES = {"PLANNED", "IMPLEMENTED_NOT_TESTED", "BUILD_PASS",
            "FUNCTIONAL_PASS", "PERFORMANCE_PASS", "PHYSICAL_PASS",
            "FAIL", "NOT_RUN", "UNSUPPORTED", "CAPACITY_LIMITED"}
PRODUCT_PREFIXES = ("crates/", "src/", "r0/go_overlay/", "r0/abi/", "native/", "openwrt/", "android/")


class CatalogError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise CatalogError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def safe_path(value):
    return (nonempty(value) and not value.startswith(("/", "-"))
            and not any(c in value for c in ("\\", ":", "\n", "\r"))
            and all(p not in ("", ".", "..") for p in value.split("/")))


def branch_ok(value):
    return (safe_path(value) and not any(c in value for c in (" ", "~", "^", "?", "*", "["))
            and ".." not in value and "@{" not in value and not value.endswith(".lock"))


def load(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    need(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def local_ref(root, value):
    need(safe_path(value), f"unsafe local reference: {value}")
    path = root / value
    need(path.is_file() and not path.is_symlink(), f"missing regular file: {value}")
    need(path.resolve().is_relative_to(root.resolve()), f"reference outside repository: {value}")


def evidence_ref(root, value):
    need(nonempty(value), "missing evidence/decision reference")
    if value.startswith("https://github.com/lly8666/"):
        need(not any(c.isspace() for c in value), "invalid evidence URL")
    else:
        local_ref(root, value)


def source_ref(root, value):
    # Metadata for unmerged experiments may live on main before their code does.
    # Pin such cross-branch references to an immutable commit, never a branch URL.
    prefix = "https://github.com/lly8666/wbd-next/blob/"
    if isinstance(value, str) and value.startswith(prefix):
        revision, _, path = value[len(prefix):].partition("/")
        need(bool(SHA.fullmatch(revision)) and safe_path(path), "cross-branch reference needs exact SOURCE/path")
    else:
        local_ref(root, value)


def validate_entry(root, path):
    item = load(path)
    need(item.get("schema_version") == 1, f"unknown schema: {path}")
    fid = item.get("id", "")
    need(isinstance(fid, str) and ID.fullmatch(fid) and path.stem == fid, "ID/filename mismatch")
    for key in ("name", "summary", "owner"):
        need(nonempty(item.get(key)), f"{fid}: missing {key}")
    need(item.get("stage") in {"experimental", "formal", "retired"}, f"{fid}: invalid stage")
    rows = item.get("verification")
    need(isinstance(rows, list) and rows and all(isinstance(x, dict) for x in rows),
         f"{fid}: verification must declare untested scopes too")
    planned = item["stage"] == "experimental" and all(x.get("status") == "PLANNED" for x in rows)
    branch = item.get("development_branch")
    need(branch_ok(branch), f"{fid}: invalid development branch")
    if item["stage"] == "experimental" and not branch.startswith("experiment/"):
        need(nonempty(item.get("legacy_branch_reason")),
             f"{fid}: new experiments belong in experiment/**; historical exceptions need a reason")
    locations = item.get("available_on")
    need(isinstance(locations, list) and all(branch_ok(x) for x in locations)
         and (locations or planned or item["stage"] == "retired"),
         f"{fid}: list actual available branches")
    need(not planned or not locations, f"{fid}: planned-only features are not yet available")
    need(len(set(locations)) == len(locations), f"{fid}: duplicate branch")
    need(isinstance(item.get("defaults"), dict), f"{fid}: defaults must be explicit (empty allowed)")
    need(isinstance(item.get("usage"), dict), f"{fid}: missing usage")
    for surface in ("cli", "config", "gui"):
        need(nonempty(item["usage"].get(surface)), f"{fid}: {surface} usage or non-applicability required")
    for key in ("code_refs", "doc_refs"):
        need(isinstance(item.get(key), list) and (item[key] or (key == "code_refs" and planned)),
             f"{fid}: missing {key}")
        for ref in item[key]:
            source_ref(root, ref)
    need(isinstance(item.get("limitations"), list) and all(nonempty(x) for x in item["limitations"]),
         f"{fid}: limitations must be a list")
    if item["stage"] == "retired":
        need(item["limitations"], f"{fid}: record retirement reason/replacement")
    scopes = set()
    for row in rows:
        need(isinstance(row, dict), f"{fid}: verification row must be an object")
        need(nonempty(row.get("platform")) and nonempty(row.get("scope")), f"{fid}: missing scope")
        identity = (row["platform"], row["scope"])
        need(identity not in scopes, f"{fid}: duplicate verification scope")
        scopes.add(identity)
        status = row.get("status")
        need(status in STATUSES, f"{fid}: unknown verification status")
        source = row.get("source_sha")
        need(source is None or (isinstance(source, str) and SHA.fullmatch(source)), f"{fid}: invalid SOURCE")
        if status.endswith("PASS") or status in {"FAIL", "CAPACITY_LIMITED"}:
            need(source is not None, f"{fid}: measured result needs exact SOURCE")
            evidence_ref(root, row.get("evidence"))
        elif row.get("evidence") is not None:
            evidence_ref(root, row["evidence"])
    promotion = item.get("promotion")
    if item["stage"] == "formal":
        need("main" in locations, f"{fid}: formal feature must be integrated into main")
        need(isinstance(promotion, dict), f"{fid}: merging alone is not promotion")
        need(isinstance(promotion.get("source_sha"), str) and SHA.fullmatch(promotion["source_sha"]),
             f"{fid}: promotion needs exact integrated SOURCE")
        evidence_ref(root, promotion.get("decision"))
        evidence_ref(root, promotion.get("evidence"))
        need(any(x["status"] in {"FUNCTIONAL_PASS", "PERFORMANCE_PASS", "PHYSICAL_PASS"} for x in rows),
             f"{fid}: formal status needs at least one qualified product scope")
    else:
        need(promotion is None, f"{fid}: only formal features carry a current promotion")
    return item


def read_catalog(root):
    state = load(root / STATE)
    need(state.get("schema_version") == 1, "invalid inventory schema")
    need(state.get("status") in {"NOT_INITIALIZED", "PARTIAL", "COMPLETE_FOR_SCOPE"}, "invalid inventory status")
    need(branch_ok(state.get("scope_branch")), "invalid inventory scope branch")
    need(isinstance(state.get("baseline_source"), str) and SHA.fullmatch(state["baseline_source"]),
         "inventory baseline must be an exact SOURCE")
    need(nonempty(state.get("next_action")), "inventory next action required")
    source = state.get("inventory_source")
    need(source is None or (isinstance(source, str) and SHA.fullmatch(source)), "invalid inventory SOURCE")
    need(isinstance(state.get("gaps"), list) and all(nonempty(x) for x in state["gaps"]), "invalid inventory gaps")
    items = {}
    for path in sorted((root / CATALOG).glob("*.json")):
        need(not path.is_symlink() and path.stat().st_size <= 16 * 1024, "feature card must be bounded regular JSON")
        item = validate_entry(root, path)
        need(item["id"] not in items, "duplicate feature ID")
        items[item["id"]] = item
    if state["status"] == "COMPLETE_FOR_SCOPE":
        need(items and not state["gaps"], "complete inventory cannot be empty or contain untriaged gaps")
        need(source is not None, "complete inventory needs the exact reviewed SOURCE")
        evidence_ref(root, state.get("review_ref"))
    return state, items


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8").strip()


def select_base(root, state, before=None):
    if before and before != "0" * 40:
        need(bool(SHA.fullmatch(before)), "invalid push base")
        git(root, "cat-file", "-e", before + "^{commit}")
        need(subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", before, "HEAD"],
                            capture_output=True).returncode == 0, "non-fast-forward push requires explicit review")
        return before
    # New branch: compare with its main fork when the gate already existed.
    # When main has not adopted the gate, derive the installation boundary from
    # history instead of a mutable JSON field. This also works for cherry-picks.
    try:
        base = git(root, "merge-base", "HEAD", "origin/main")
        if subprocess.run(["git", "-C", str(root), "cat-file", "-e", base + ":" + STATE],
                          capture_output=True).returncode == 0:
            return base
    except subprocess.CalledProcessError:
        pass
    installations = git(root, "log", "--diff-filter=A", "--format=%H", "--", STATE).splitlines()
    need(installations, "missing catalog installation history")
    installation = installations[-1]
    parents = git(root, "rev-list", "--parents", "-n", "1", installation).split()
    # A new repository with the gate in its root commit compares against empty.
    return parents[1] if len(parents) > 1 else subprocess.check_output(
        ["git", "-C", str(root), "hash-object", "-t", "tree", "--stdin"], input="", text=True).strip()


def product_path(path):
    return (path.startswith(PRODUCT_PREFIXES)
            or path in {"Cargo.toml", "Cargo.lock"}
            or (path.startswith(("config/", "configs/", "examples/")) and path.endswith((".json", ".toml", ".yaml", ".yml"))))


def check_change(root, changed, items):
    relevant = [p for p in changed if product_path(p)]
    cards = [p for p in changed if p.startswith(CATALOG) and p.endswith(".json")]
    if not relevant and not cards:
        return "NO_PRODUCT_OR_FEATURE_CHANGE"
    ids = set()
    found = False
    for path in changed:
        if not path.startswith("docs/devlog/") or not path.endswith(".md") or not (root / path).is_file():
            continue
        body = (root / path).read_text(encoding="utf-8")
        for match in re.finditer(r"```feature-impact\s*\n(.*?)\n```", body, re.S):
            note = json.loads(match.group(1))
            need(isinstance(note, dict), "feature-impact must be a JSON object")
            need(note.get("kind") in {"updated", "none"}, "invalid feature-impact kind")
            need(nonempty(note.get("reason")), "feature-impact explanation required")
            listed = note.get("ids")
            need(isinstance(listed, list) and all(isinstance(x, str) and ID.fullmatch(x) for x in listed),
                 "invalid feature-impact IDs")
            need((note["kind"] == "updated" and listed) or (note["kind"] == "none" and not listed),
                 "feature-impact kind/IDs inconsistent")
            found = True
            ids.update(listed)
    need(found, "product change requires a feature-impact block in its changed devlog")
    for fid in ids:
        need(fid in items, f"feature-impact refers to missing feature: {fid}")
        need(CATALOG + fid + ".json" in changed, f"declared feature card not updated: {fid}")
    for path in cards:
        fid = PurePosixPath(path).stem
        need(fid in items, "do not silently delete a feature; mark retired with explanation")
        need(fid in ids, f"changed feature lacks devlog declaration: {fid}")
    return "DECLARED_UPDATED" if ids else "DECLARED_NO_FEATURE_IMPACT"


def render(state, items, query="", source=None):
    lines = ["# 当前分支功能索引", "",
             f"盘点状态：{state['status']}；范围：`{state['scope_branch']}`。不是全平台 PASS。", "",
             "| 功能 | 性质 | 开发分支 | 已存在分支 | 验证范围 |", "|---|---|---|---|---|"]
    for fid, item in items.items():
        if query and query.lower() not in json.dumps(item, ensure_ascii=False).lower():
            continue
        clean = lambda s: str(s).replace("|", "/").replace("\n", " ")
        proof = "; ".join(f"{x['platform']} {x['scope']}: {x['status']}" for x in item["verification"])
        link = f"https://github.com/lly8666/wbd-next/blob/{source}/{CATALOG}{fid}.json" if source else f"entries/{fid}.json"
        lines.append(f"| [{clean(item['name'])}]({link}) | {item['stage']} | {clean(item['development_branch'])} | {clean(', '.join(item['available_on']))} | {clean(proof)} |")
    if not items:
        lines.append("\n尚未初始化产品功能条目；不得据此认定产品没有功能。")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "list"])
    parser.add_argument("--base", help="exact comparison commit; defaults to Actions push before")
    parser.add_argument("--query", default="")
    parser.add_argument("--output", help="write generated index, not a second source of truth")
    args = parser.parse_args()
    state, items = read_catalog(ROOT)
    if args.command == "list":
        rendered = render(state, items, args.query, git(ROOT, "rev-parse", "HEAD"))
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered)
        return
    before = args.base
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if before is None and event_path and os.environ.get("GITHUB_EVENT_NAME") == "push":
        before = load(Path(event_path)).get("before")
    base = select_base(ROOT, state, before)
    raw = git(ROOT, "diff", "--name-only", "--no-renames", "-z", base, "HEAD")
    changed = [p for p in raw.split("\0") if p]
    result = check_change(ROOT, changed, items)
    print(json.dumps({"result": "PASS", "scope": "feature_catalog_structure_and_declaration_only",
                      "source": git(ROOT, "rev-parse", "HEAD"), "base": base,
                      "inventory": state["status"], "features": len(items), "change": result,
                      "product_tests": "NOT_RUN", "semantic_completeness": "HUMAN_REVIEW_REQUIRED"}))


if __name__ == "__main__":
    try:
        main()
    except (CatalogError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Feature catalog FAIL: {exc}")
