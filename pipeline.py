import time
import uuid
import json
import random
import boto3
from datetime import datetime, timezone


_idempotency_store = {}   # NEW: module-level store, key -> record


def fake_llm(prompt):
    time.sleep(random.uniform(0.1, 0.5))
    if random.random() < 0.3:
        raise TimeoutError("fake LLM timed out")
    return f"Answer to: {prompt}"

_bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def real_llm(prompt, model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0"):
    resp = _bedrock.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 300, "temperature": 0.7},
    )
    return resp["output"]["message"]["content"][0]["text"]


def traced_llm_call(prompt, llm=fake_llm, log_file="runs.jsonl",
                    max_retries=3,
                    fallback="[fallback] Service busy, please try again later.",
                    confidence_threshold=0.7,
                    idempotency_key=None):                       # NEW param

    # --- idempotency check: process se pehle ---            # NEW block
    if idempotency_key is not None and idempotency_key in _idempotency_store:
        return _idempotency_store[idempotency_key]            # cached, dobara process nahi

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

    fallback_used = False
    if not ok:
        output = fallback
        fallback_used = True

    confidence = None
    needs_review = False
    if ok:
        confidence = round(random.uniform(0.5, 1.0), 2)
        if confidence < confidence_threshold:
            needs_review = True

    latency_ms = (time.perf_counter() - start) * 1000

    record = {
        "run_id": run_id,
        "ok": ok,
        "output": output,
        "error": error,
        "attempts": attempts,
        "fallback_used": fallback_used,
        "confidence": confidence,
        "needs_review": needs_review,
        "idempotency_key": idempotency_key,                  # NEW field
        "latency_ms": round(latency_ms, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(record) + "\n")

    # --- store for idempotency: return se pehle ---         # NEW block
    if idempotency_key is not None:
        _idempotency_store[idempotency_key] = record

    return record

def handler(event, context):
    prompt = event.get("prompt", "Hello from Lambda")
    result = traced_llm_call(prompt, llm=real_llm, log_file="/tmp/runs.jsonl")
    return {"statusCode": 200, "body": json.dumps(result)}


if __name__ == "__main__":
    results = [traced_llm_call(f"question {i}") for i in range(10)]
    ok = sum(1 for r in results if r["ok"])
    avg = sum(r["latency_ms"] for r in results) / len(results)
    print(f"Success: {ok}/10, Avg latency: {avg:.1f} ms")

    # idempotency test                                       # NEW
    r1 = traced_llm_call("hello", idempotency_key="abc")
    r2 = traced_llm_call("hello", idempotency_key="abc")
    print("same run_id (idempotent):", r1["run_id"] == r2["run_id"])