"""
FastAPI entrypoint. This file's only job is to be the "web layer":
receive HTTP requests, validate them (via the Pydantic schemas), call
the core analyze() function, and return the result as JSON.

Exactly 2 endpoints live here, per the project spec. No extra endpoints
(not even a /health check) -- the spec explicitly says extra endpoints
count against you.
"""

from fastapi import FastAPI

from app.schemas import AnalyzeRequest, AnalyzeResponse, PolicyResponse
from app.core.detectors import analyze

app = FastAPI(title="SentraGuard Lite")

# The policy is just a plain Python dict for this MVP. In production
# this might be loaded from a config file or a database instead of
# being hardcoded here.
POLICY = {
    "version": "1",
    "detectors": ["prompt_injection", "pii", "rag_injection"],
    "thresholds": {"block_score": 80, "transform_score": 40},
}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(request: AnalyzeRequest) -> dict:
    """
    request is already validated by Pydantic by the time this function
    runs -- if the JSON body didn't match AnalyzeRequest's shape,
    FastAPI would have returned a 422 error automatically, and this
    code would never execute.
    """
    context_docs = [doc.model_dump() for doc in request.context_docs]
    result = analyze(request.prompt, context_docs, POLICY["thresholds"])
    return result


@app.get("/policy", response_model=PolicyResponse)
def policy_endpoint() -> dict:
    return POLICY
