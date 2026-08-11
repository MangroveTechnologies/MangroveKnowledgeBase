#!/usr/bin/env python3
"""Run every audit and the ontology build, once, with a single pass/fail exit code.

The audits verify our implementations against a reference library and against each other. They were
written to be run by hand, one at a time, which means in practice they were run when someone
remembered -- and six of them appeared to be broken for months because of the trap below.

**The trap: `import mangrove_kb` may not be this repository.** A copy installed in site-packages
shadows the checkout unless the repo is first on `sys.path`, and most of these scripts never put it
there. Run by hand from the repo root they silently audited the *installed* package: `audit_wave_b`
reported `MAMA missing data: ['close']` and `audit_wave_e` an ImportError for a class that exists
here, both from a stale install. Every child gets `PYTHONPATH` pointing at the repo, and the run
aborts if the import still resolves elsewhere -- a green audit of the wrong code is worse than a red
one.

The ontology build runs too, and not as a formality: it carries nine `sys.exit(1)` invariants --
dangling edges, `about` edges with no `uses` behind them, half-authored outputs, a signal whose
derived class contradicts its module -- and those only fire when it actually builds. It writes to a
temporary path, never over the committed graph.

Usage:
    python scripts/audit/run_all.py              # everything
    python scripts/audit/run_all.py --quick      # skip the slow formula verifier
    python scripts/audit/run_all.py -v           # stream each script's own output
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
BUILDER = REPO / "ontology" / "build_signal_indicator_ontology.py"

#: Minutes, not seconds: `verify_signal_formulas` re-derives every signal's formula symbolically.
#: Excluded by `--quick` so the common case stays fast, and named in the summary when it is.
SLOW = {"verify_signal_formulas.py"}

#: Discovered, never hand-listed. A hard-coded list silently drops whichever script gets added next,
#: which is the failure this whole file exists to stop.
def audit_scripts() -> list[Path]:
    return sorted(p for p in HERE.glob("*.py")
                  if p.name not in {"__init__.py", "config.py", "compare.py", "report.py",
                                    Path(__file__).name})


def child_env() -> dict[str, str]:
    """The repo first on the import path, for every child."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    return env


def check_import_is_this_repo(env: dict[str, str]) -> str | None:
    """Refuse to run against a different copy of the package than the one being audited."""
    proc = subprocess.run([sys.executable, "-c", "import mangrove_kb; print(mangrove_kb.__file__)"],
                          capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)
    loaded = Path(proc.stdout.strip() or "?")
    expected = REPO / "mangrove_kb" / "__init__.py"
    if loaded != expected:
        return f"`import mangrove_kb` resolves to {loaded}, not {expected}"
    return None


def run(cmd: list[str], env: dict[str, str], timeout: int) -> tuple[str, float, str]:
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                              cwd=str(REPO), timeout=timeout)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", time.monotonic() - started, f"exceeded {timeout}s"
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    # 77 is the conventional "skipped" code. A script opts out this way when a reference library it
    # needs is not on this machine -- reported as SKIP, never folded into the pass count.
    status = {0: "PASS", 77: "SKIP"}.get(proc.returncode, "FAIL")
    return status, time.monotonic() - started, tail[-1][:70] if tail else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help=f"skip the slow ones: {sorted(SLOW)}")
    ap.add_argument("--timeout", type=int, default=900, help="per-script seconds (default 900)")
    ap.add_argument("-v", "--verbose", action="store_true", help="stream each script's output")
    args = ap.parse_args()

    env = child_env()
    wrong = check_import_is_this_repo(env)
    if wrong:
        print(f"ABORT: {wrong}\n  Every result would describe the wrong code. Check for an installed "
              f"copy shadowing the checkout.", file=sys.stderr)
        return 2

    jobs: list[tuple[str, list[str]]] = []
    with tempfile.TemporaryDirectory() as tmp:
        # First, because the invariants it carries are the strongest checks in the repo, and a
        # broken graph makes several audits meaningless. NEVER over the committed file.
        build_env = {**env, "ONTOLOGY_OUT": str(Path(tmp) / "ontology.json")}
        jobs.append(("ontology build", [sys.executable, str(BUILDER)]))

        skipped = [s.name for s in audit_scripts() if args.quick and s.name in SLOW]
        for script in audit_scripts():
            if script.name in skipped:
                continue
            jobs.append((script.name, [sys.executable, str(script)]))

        print(f"running {len(jobs)} checks against {REPO}\n")
        results = []
        for name, cmd in jobs:
            e = build_env if name == "ontology build" else env
            if args.verbose:
                print(f"--- {name}")
                proc = subprocess.run(cmd, env=e, cwd=str(REPO), timeout=args.timeout)
                status, secs, note = ("PASS" if proc.returncode == 0 else "FAIL"), 0.0, ""
            else:
                status, secs, note = run(cmd, e, args.timeout)
            results.append((name, status))
            mark = {"PASS": "ok  ", "FAIL": "FAIL", "TIMEOUT": "TIME", "SKIP": "skip"}[status]
            print(f"  {mark}  {name:<30} {secs:6.1f}s  {note}")

    failed = [n for n, st in results if st in ("FAIL", "TIMEOUT")]
    opted_out = [n for n, st in results if st == "SKIP"]
    print()
    # Never silent: a run that skipped something must say what, or "all green" is a lie.
    if skipped:
        print(f"SKIPPED (--quick): {', '.join(skipped)}")
    if opted_out:
        print(f"SKIPPED (reference library absent): {', '.join(opted_out)}")
    ran = len(results) - len(opted_out)
    print(f"{ran - len(failed)}/{ran} passed"
          + (f" -- FAILED: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
