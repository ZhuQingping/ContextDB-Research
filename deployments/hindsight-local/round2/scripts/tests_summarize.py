#!/usr/bin/env python3
"""Summarize durable test artifacts without treating skips/collection as passes."""
from pathlib import Path
import collections,json,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]/'evidence'; rows=[]
for d in sorted(root.glob('tests-*')):
 if not d.is_dir():continue
 row={'suite':d.name}
 c=d/'command.json'
 if c.exists():
  meta=json.loads(c.read_text()); row.update({k:meta[k] for k in ['exit_code','duration_seconds']})
 p=d/'junit.xml'
 if p.exists():
  r=ET.parse(p).getroot();tests=list(r.iter('testcase'))
  row.update({'junit_cases':len(tests),'failures':sum(t.find('failure') is not None for t in tests),'errors':sum(t.find('error') is not None for t in tests),'skipped_or_xfailed':sum(t.find('skipped') is not None for t in tests)})
 rows.append(row)
(root/'tests-summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
