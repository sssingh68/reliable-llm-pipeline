from pipeline import traced_llm_call

# --- test doubles: predictable LLMs for deterministic evals ---
def always_ok_llm(prompt):
    return f"OK: {prompt}"

def always_fail_llm(prompt):
    raise TimeoutError("simulated failure")

# --- eval cases: each checks one behaviour of the pipeline ---
# (name, which llm to inject, prompt, check function on the result record)
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
    passed = 0
    for name, llm, prompt, check in EVAL_CASES:
        result = traced_llm_call(prompt, llm=llm, log_file="eval_runs.jsonl")
        ok = check(result)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if ok:
            passed += 1
    total = len(EVAL_CASES)
    print(f"\n{passed}/{total} evals passed")
    return passed, total


if __name__ == "__main__":
    run_evals()