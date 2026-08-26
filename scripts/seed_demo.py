import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.analyzer import TEST_CASES, analyze  # noqa: E402
from app.repository import ScanRepository  # noqa: E402

repository = ScanRepository()
for test_case in TEST_CASES:
    analysis = analyze(test_case['content'], test_case['scan_type'])
    repository.save_scan(test_case['content'], analysis)
print(f'Seeded {len(TEST_CASES)} public test scans into the local database.')
