import time
import uuid
import json
import random
from datetime import datetime, timezone


def fake_llm(prompt):                      # ← dabba 1
    time.sleep(random.uniform(0.1, 0.5))
    if random.random() < 0.3:
        raise TimeoutError("fake LLM timed out")
    return f"Answer to: {prompt}"


def traced_llm_call(prompt, llm=fake_llm, log_file="runs.jsonl",
                    max_retries=3,
                    fallback="[fallback] Service busy, please try again later."):   # NEW: fallback param
    run_id = str(uuid.uuid4())
    start = time.perf_counter()

    output = None
    ok = False
    error = None
    attempts = 0

    for attempt in range(max_retries):
        attempts = attempt + 1
        try:
            output = llm(prompt)
            ok = True
            error = None
            break
        except Exception as e:
            error = str(e)
            ok = False
            if attempt < max_retries - 1:
                backoff = 2 ** attempt
                time.sleep(backoff)

    fallback_used = False                # NEW
    if not ok:                           # NEW: saari retries fail hui
        output = fallback                # NEW: safe default do
        fallback_used = True             # NEW: flag set

    latency_ms = (time.perf_counter() - start) * 1000

    record = {
        "run_id": run_id,
        "ok": ok,                        # ok abhi bhi False (real success nahi)
        "output": output,                # ab fallback text hai, None nahi
        "error": error,
        "attempts": attempts,
        "fallback_used": fallback_used,  # NEW: metric field
        "latency_ms": round(latency_ms, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(record) + "\n")

    return record


if __name__ == "__main__":                 # ← dabba 3 (bilkul left se, bahar)
    results = [traced_llm_call(f"question {i}") for i in range(10)]
    ok = sum(1 for r in results if r["ok"])
    avg = sum(r["latency_ms"] for r in results) / len(results)
    print(f"Success: {ok}/10, Avg latency: {avg:.1f} ms")