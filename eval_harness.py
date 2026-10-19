import json
import os
from pipeline import traced_llm_call

BASELINE_FILE = "baseline.json"

# --- test doubles ---
def always_ok_llm(prompt):
    return f"OK: {prompt}"

def always_fail_llm(prompt):
    raise TimeoutError("simulated failure")

# --- eval cases ---
EVAL_CASES = [
    ("returns output on success",
     always_ok_llm, "hello",
     lambda r: r["ok"] is True and r["output"].startswith("OK:")),
    ("falls back when llm always fails",
     always_fail_llm, "hello",
     lambda r: r["ok"] is False and r["fallback_used"] is True),
    ("record always has required fields",
     always_ok_llm, "hi",
     lambda r: all(k in r for k in ["run_id", "ok", "latency_ms", "timestamp"])),
]

def run_evals():
    results = {}
    for name, llm, prompt, check in EVAL_CASES:
        record = traced_llm_call(prompt, llm=llm, log_file="eval_runs.jsonl")
        results[name] = check(record)
    return results

def print_results(results):
    for name, ok in results.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    passed = sum(1 for ok in results.values() if ok)
    print(f"\n{passed}/{len(results)} evals passed")

def save_baseline(results):
    with open(BASELINE_FILE, "w") as f:
        json.dump(results, f, indent=2)

def check_regressions(results):
    if not os.path.exists(BASELINE_FILE):
        print("\nNo baseline yet — saving current results as baseline.")
        save_baseline(results)
        return
    with open(BASELINE_FILE) as f:
        baseline = json.load(f)
    regressions = [name for name, ok in results.items()
                   if baseline.get(name) is True and ok is False]
    if regressions:
        print("\n[!] REGRESSIONS (passed before, now failing):")
        for name in regressions:
            print(f"    - {name}")
    else:
        print("\nNo regressions vs baseline.")


if __name__ == "__main__":
    results = run_evals()
    print_results(results)
    check_regressions(results)