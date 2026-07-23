

from typing import Optional
from pydantic import BaseModel, Field


class ContextDoc(BaseModel):
    id: str
    text: str


class Metadata(BaseModel):
    # All optional: metadata is "nice to have", not required to analyze.
    app_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None


class AnalyzeRequest(BaseModel):
    prompt: str
    # default_factory=list means "if not provided, use an empty list"
    context_docs: list[ContextDoc] = Field(default_factory=list)
    metadata: Optional[Metadata] = None


class Reason(BaseModel):
    tag: str
    evidence: str


class AnalyzeResponse(BaseModel):
    decision: str
    risk_score: int
    risk_tags: list[str]
    sanitized_prompt: str
    sanitized_context_docs: list[ContextDoc]
    reasons: list[Reason]


class PolicyResponse(BaseModel):
    version: str
    detectors: list[str]
    thresholds: dict
