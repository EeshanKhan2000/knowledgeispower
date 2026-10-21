"""Monitor collaborator branches: what's new since the last check, and does it matter?

    python scripts/monitor_contrib.py              # report only (markdown to stdout)
    python scripts/monitor_contrib.py --run-tests  # also run pytest on each changed branch, in an isolated worktree

For every remote branch except main and the core development branch, the report shows:
- commits since the last check (author, subject) and commits ahead of the core branch;
- files changed vs. the core branch, with **protected-path violations** flagged (mirrors .github/CODEOWNERS);
- new or changed files under results/contrib/, with headline numbers when they are JSON verdicts or comparisons;
- the S1 `IMPLEMENTED` flag, if the branch touches contrib/variant_bridge;
- test results (with --run-tests).

State (the last-seen SHA per branch) lives in data/cache/monitor_state.json, which is gitignored.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "cache" / "monitor_state.json"
CORE = "origin/claude/happy-hamilton-kdexid"
SKIP = {"origin/main", CORE, "origin/HEAD"}
PROTECTED = ("src/scp_graphfs_mcp/", "benchmarks/", "data/", "AGENTS.md", ".github/", "results/")
ALLOWED_RESULTS = "results/contrib/"


def git(*a: str) -> str:
    return subprocess.check_output(["git", *a], cwd=ROOT, text=True).strip()


def protected(path: str) -> bool:
    if path.startswith(ALLOWED_RESULTS):
        return False
    if path.startswith("tests/test_") and "/" not in path[len("tests/"):]:
        return True  # acceptance tests: add-only, flag any edit for review
    return path.startswith(PROTECTED)


def summarise_result(branch: str, path: str) -> str:
    try:
        d = json.loads(git("show", f"{branch}:{path}"))
    except Exception:  # noqa: BLE001
        return ""
    keys = [k for k in ("primary_confirmed", "primary_passes", "test1_pass", "test2_pass") if k in d]
    return ", ".join(f"{k}={d[k]}" for k in keys)


def run_tests(branch: str) -> str:
    with tempfile.TemporaryDirectory(dir=ROOT / "data" / "cache") as tmp:
        wt = Path(tmp) / "wt"
        git("worktree", "add", "--detach", str(wt), branch)
        try:
            env = {"PYTHONPATH": f"{wt / 'src'}:{wt}", "PATH": "/usr/bin:/bin"}
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-m", "not network", "-p", "no:cacheprovider"],
                               cwd=wt, env=env, text=True, capture_output=True, timeout=900)
            return (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        finally:
            git("worktree", "remove", "--force", str(wt))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-tests", action="store_true")
    ap.add_argument("--no-save", action="store_true", help="don't update the last-seen state")
    a = ap.parse_args()
    git("fetch", "-q", "--all", "--prune")
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    branches = [b.strip() for b in git("branch", "-r").splitlines() if "->" not in b]
    branches = [b for b in branches if b not in SKIP]
    out = [f"## Collaborator branch monitor · core = `{CORE}` @ `{git('rev-parse', '--short', CORE)}`", ""]
    interesting = False
    for b in sorted(branches):
        sha = git("rev-parse", b)
        last = state.get(b)
        ahead = git("rev-list", "--count", f"{CORE}..{b}")
        behind = git("rev-list", "--count", f"{b}..{CORE}")
        new = git("log", "--format=%h %an: %s", f"{last}..{b}") if last and last != sha else ("" if last else
              git("log", "--format=%h %an: %s", f"{CORE}..{b}"))
        files = [f for f in git("diff", "--name-only", f"{CORE}...{b}").splitlines() if f]
        viol = [f for f in files if protected(f)]
        res = [f for f in files if f.startswith(ALLOWED_RESULTS)]
        status = "unchanged since last check" if last == sha else ("new branch" if not last else "NEW COMMITS")
        out += [f"### `{b}`: {status}", f"- {ahead} commit(s) ahead of core, {behind} behind; head `{sha[:7]}`"]
        if new:
            interesting = True
            out += ["- New commits:"] + [f"  - {line}" for line in new.splitlines()[:20]]
        if files:
            out.append(f"- Files changed vs core: {len(files)} ({', '.join(files[:8])}{' …' if len(files) > 8 else ''})")
        if viol:
            interesting = True
            out.append(f"- ⚠️ **Protected paths touched** (need Amit's review): {', '.join(viol)}")
        for f in res:
            interesting = True
            s = summarise_result(b, f)
            out.append(f"- 📊 New contrib result `{f}`" + (f": {s}" if s else ""))
        if any(f.startswith("contrib/variant_bridge/") for f in files):
            impl = "IMPLEMENTED = True" in git("show", f"{b}:contrib/variant_bridge/variant_bridge.py")
            out.append(f"- S1 `IMPLEMENTED` flag: {impl}")
        if a.run_tests and (new or not last) and files:
            out.append(f"- Tests: `{run_tests(b)}`")
        out.append("")
        state[b] = sha
    if not branches:
        out.append("_No collaborator branches._")
    out.append(f"**Anything new worth acting on: {'YES' if interesting else 'no'}**")
    print("\n".join(out))
    if not a.no_save:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=1))


if __name__ == "__main__":
    main()
