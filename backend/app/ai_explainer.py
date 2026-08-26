import json
import os
from typing import Any

from .schemas import Analysis

SYSTEM_PROMPT = """You are ScamShield's safety explanation assistant. Explain the existing detector result in plain, calm language. Do not change the score, verdict, findings, or confidence. Never tell users to click links, share credentials, or pay money. Return JSON with exactly one string field named explanation, under 280 characters."""


def ai_is_configured() -> bool:
    return bool(os.getenv('OPENAI_API_KEY')) and os.getenv('AI_ANALYSIS_ENABLED', 'false').lower() == 'true'


def enhance_explanation(content: str, analysis: Analysis) -> str | None:
    """Return an optional LLM explanation; failures always fall back to rules output."""
    if not ai_is_configured():
        return None

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ['OPENAI_API_KEY'],
            timeout=float(os.getenv('AI_TIMEOUT_SECONDS', '8')),
            max_retries=1,
        )
        response = client.chat.completions.create(
            model=os.getenv('AI_MODEL', 'gpt-4o-mini'),
            temperature=0.1,
            response_format={'type': 'json_object'},
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': json.dumps({
                    'content': content[:10_000],
                    'score': analysis.score,
                    'verdict': analysis.verdict,
                    'findings': [finding.model_dump(exclude_none=True) for finding in analysis.findings],
                })},
            ],
        )
        raw = response.choices[0].message.content or '{}'
        result: Any = json.loads(raw)
        explanation = result.get('explanation')
        return explanation.strip() if isinstance(explanation, str) and explanation.strip() else None
    except Exception:
        return None
