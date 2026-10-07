"""Read-only delivery checks; write a bounded manifest, never print credentials."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import re
import subprocess
import urllib.request

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
DOCS = [ROOT / 'hindsight' / name for name in (
    'Huawei ContextDB Service Develop.md', 'cloud-service-architecture.md',
    'cloud-service-priorities.md')]
DOCS += [BASE / 'README.md', *sorted((BASE / 'reports').glob('*.md'))]
missing = []
links = 0
for path in DOCS:
    for raw in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        target = raw.strip('<>').split('#')[0]
        if not target or '://' in target:
            continue
        links += 1
        if not (path.parent / target).exists():
            missing.append({'file': str(path.relative_to(ROOT)), 'target': target})
syntax_errors = []
scripts = sorted((BASE / 'scripts').glob('*.py'))
for path in scripts:
    try:
        ast.parse(path.read_text())
    except SyntaxError as exc:
        syntax_errors.append({'file': path.name, 'error': str(exc)})
health = {}
for name, url in [('api', 'http://127.0.0.1:8888/health'), ('ui', 'http://127.0.0.1:9999/')]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            health[name] = {'status': response.status}
    except Exception as exc:
        health[name] = {'error_type': type(exc).__name__}
source = ROOT.parent / 'hindsight'
sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
clean = not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip()
artifacts = DOCS + scripts + sorted((BASE / 'evidence').glob('*.json'))
checks = {
    'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_sha': sha, 'upstream_worktree_clean': clean,
    'markdown_files': len(DOCS), 'local_links_checked': links,
    'missing_links': missing, 'python_scripts_checked': len(scripts),
    'syntax_errors': syntax_errors, 'original_service_health': health,
    'scope': 'artifact/source/health checks, not product acceptance or an eight-hour soak',
}
(BASE / 'evidence' / 'delivery-checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n')
artifacts = [p for p in artifacts if p.name not in ('delivery-manifest.json', 'delivery-checks.json')]
manifest = {'checked_at_utc': checks['checked_at_utc'], 'files': [
    {'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
     'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in artifacts
]}
(BASE / 'evidence' / 'delivery-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(checks, ensure_ascii=False))
raise SystemExit(1 if missing or syntax_errors or not clean or any(v.get('status') != 200 for v in health.values()) else 0)
