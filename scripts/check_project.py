from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ('app/page.tsx', 'lib/api.ts', 'backend/app/main.py', 'backend/app/analyzer.py', 'backend/tests/test_api.py', 'README.md')
missing = [path for path in REQUIRED if not (ROOT / path).exists()]
if missing:
    raise SystemExit(f'Missing required project files: {", ".join(missing)}')
source_files = [path for path in ROOT.rglob('*') if path.suffix in {'.ts', '.tsx', '.py', '.mjs'} and 'node_modules' not in path.parts and '.next' not in path.parts]
print(f'ScamShield structure check passed: {len(source_files)} source files')
