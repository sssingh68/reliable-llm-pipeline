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


def traced_llm_call(prompt, llm=fake_llm, log_file="runs.jsonl", max_retries=3):
    run_id = str(uuid.uuid4())
    start = time.perf_counter()

    output = None
    ok = False
    error = None
    attempts = 0

    for attempt in range(max_retries):        # attempt = 0, 1, 2
        attempts = attempt + 1                 # insaani ginti (1,2,3)
        try:
            output = llm(prompt)
            ok = True
            error = None
            break                              # success → loop rok do
        except Exception as e:
            error = str(e)
            ok = False
            if attempt < max_retries - 1:      # aakhri attempt nahi to hi ruko
                backoff = 2 ** attempt         # TODO samjho: 1, 2, 4 sec
                time.sleep(backoff)

    latency_ms = (time.perf_counter() - start) * 1000

    record = {
        "run_id": run_id,
        "ok": ok,
        "output": output,
        "error": error,
        "attempts": attempts,                  # NAYA: kitni koshish lagi
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