from .ai_explainer import enhance_explanation
from .analyzer import analyze
from .metrics import metrics
from .schemas import Analysis, ScanType


def analyze_content(content: str, scan_type: ScanType) -> Analysis:
    analysis = analyze(content, scan_type)
    ai_explanation = enhance_explanation(content, analysis)
    if ai_explanation:
        analysis.summary = ai_explanation
    metrics.record(analysis)
    return analysis
