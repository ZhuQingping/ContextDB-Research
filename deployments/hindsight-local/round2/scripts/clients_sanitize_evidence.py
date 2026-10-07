from pathlib import Path
import json,re
b=Path(__file__).resolve().parents[1]
secrets=[]
s=json.loads((Path.home()/'.claude/settings.json').read_text()).get('env',{})
for k,v in s.items():
 if 'TOKEN' in k or 'API_KEY' in k:
  if isinstance(v,str) and len(v)>8:secrets.append(v)
for line in s.get('ANTHROPIC_CUSTOM_HEADERS','').splitlines():
 if ':' in line:secrets.append(line.split(':',1)[1].strip())
a=json.loads((b.parent/'.secrets/codex/auth.json').read_text()).get('tokens',{})
secrets.extend(v for v in a.values() if isinstance(v,str) and len(v)>8)
g=b/'clients-work/openclaw-profile/gateway-token.private'
if g.exists():secrets.append(g.read_text().strip())
counts={'secret_value_matches_redacted':0,'thinking_blocks_removed':0,'files_checked':0}
for f in (b/'evidence').glob('clients-*'):
 if not f.is_file():continue
 try:text=f.read_text()
 except UnicodeDecodeError:continue
 counts['files_checked']+=1
 for secret in secrets:
  if secret:
   counts['secret_value_matches_redacted']+=text.count(secret);text=text.replace(secret,'[REDACTED]')
 if f.name.startswith('clients-claude-') and f.suffix=='.jsonl':
  out=[]
  for line in text.splitlines():
   try:d=json.loads(line)
   except json.JSONDecodeError:out.append(line);continue
   if d.get('type')=='system' and d.get('subtype')=='thinking_tokens':continue
   content=d.get('message',{}).get('content')
   if isinstance(content,list):
    filtered=[x for x in content if not isinstance(x,dict) or x.get('type') not in ['thinking','redacted_thinking']]
    counts['thinking_blocks_removed']+=len(content)-len(filtered);d['message']['content']=filtered
    if not filtered:continue
   out.append(json.dumps(d,ensure_ascii=False))
  text='\n'.join(out)+'\n'
 f.write_text(text)
(b/'evidence/clients-redaction-audit.json').write_text(json.dumps(counts,indent=2))
print(json.dumps(counts))
