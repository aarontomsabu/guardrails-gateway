

import re


# 1. Prompt injection / jailbreak detector

INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "disregard all previous instructions",
    "reveal your system prompt",
    "reveal the system prompt",
    "show me your system prompt",
    "act as dan",
    "you are now dan",
    "jailbreak",
    "bypass your guidelines",
    "bypass your rules",
    "ignore your rules",
]


def detect_prompt_injection(text: str) -> list[dict]:

    text_lower = text.lower()
    reasons = []
    for phrase in INJECTION_PHRASES:
        if phrase in text_lower:
            reasons.append({
                "tag": "prompt_injection",
                "evidence": f"matched phrase: {phrase}",
            })
    return reasons


# 2. PII detection + redaction (emails, phone numbers)

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Matches common phone formats: 555-123-4567, (555) 123-4567, +1 555 123 4567
PHONE_PATTERN = re.compile(
    r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)


def redact_pii(text: str) -> tuple[str, list[dict]]:
    """
    Find and redact emails + phone numbers in `text`.
    Returns (redacted_text, reasons).
    We never put the raw matched value in `reasons` -- only that a match
    of a given type occurred. This satisfies the "don't log raw PII" rule.
    """
    reasons: list[dict] = []

    def replace_email(match: re.Match) -> str:
        reasons.append({"tag": "pii", "evidence": "matched email pattern"})
        return "[REDACTED_EMAIL]"

    def replace_phone(match: re.Match) -> str:
        reasons.append({"tag": "pii", "evidence": "matched phone pattern"})
        return "[REDACTED_PHONE]"

    text = EMAIL_PATTERN.sub(replace_email, text)
    text = PHONE_PATTERN.sub(replace_phone, text)
    return text, reasons


# 3. RAG injection detector (malicious instructions hidden in retrieved docs)

RAG_INJECTION_PHRASES = [
    "system:",
    "override policy",
    "ignore guidelines",
    "ignore previous instructions",
    "new instructions:",
]


def detect_rag_injection(context_docs: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Scan each retrieved context document for injection phrases, and also
    redact any PII found inside them (docs can leak PII too).

    Returns (sanitized_docs, reasons) where sanitized_docs is the same
    list of docs but with PII redacted from their text.
    """
    reasons: list[dict] = []
    sanitized_docs: list[dict] = []

    for doc in context_docs:
        doc_id = doc["id"]
        text = doc["text"]
        text_lower = text.lower()

        for phrase in RAG_INJECTION_PHRASES:
            if phrase in text_lower:
                reasons.append({
                    "tag": "rag_injection",
                    "evidence": f"doc '{doc_id}' matched phrase: {phrase}",
                })

        sanitized_text, pii_reasons = redact_pii(text)
        reasons.extend(pii_reasons)
        sanitized_docs.append({"id": doc_id, "text": sanitized_text})

    return sanitized_docs, reasons


# 4. Risk scoring

def compute_risk_score(reasons: list[dict]) -> tuple[int, list[str]]:
    
    tags = sorted(set(r["tag"] for r in reasons))

    score = 0
    if "prompt_injection" in tags:
        score += 60
    if "rag_injection" in tags:
        score += 50
    if "pii" in tags:
        score += 30

    score = min(score, 100)
    return score, tags


# 5. The orchestrator: ties all detectors together into one decision

def analyze(prompt: str, context_docs: list[dict], thresholds: dict) -> dict:
    
    injection_reasons = detect_prompt_injection(prompt)
    sanitized_prompt, pii_reasons = redact_pii(prompt)
    sanitized_docs, rag_reasons = detect_rag_injection(context_docs)

    all_reasons = injection_reasons + pii_reasons + rag_reasons
    score, tags = compute_risk_score(all_reasons)

    if score >= thresholds["block_score"]:
        decision = "block"
    elif score >= thresholds["transform_score"]:
        decision = "transform"
    else:
        decision = "allow"

    return {
        "decision": decision,
        "risk_score": score,
        "risk_tags": tags,
        "sanitized_prompt": sanitized_prompt,
        "sanitized_context_docs": sanitized_docs,
        "reasons": all_reasons,
    }
