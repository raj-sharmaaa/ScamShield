from collections import Counter
from .schemas import Analysis

class AnalysisMetrics:
    def __init__(self) -> None:
        self._verdicts: Counter[str] = Counter()
        self._total = 0

    def record(self, analysis: Analysis) -> None:
        self._total += 1
        self._verdicts[analysis.verdict] += 1

    def snapshot(self) -> dict[str, int]:
        return {'requests': self._total, 'high_risk': self._verdicts['High risk'], 'caution': self._verdicts['Caution'], 'safe': self._verdicts['Safe']}

metrics = AnalysisMetrics()
