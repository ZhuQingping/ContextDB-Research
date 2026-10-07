#!/usr/bin/env python3
"""Redact credential-shaped test values without printing matches; retain counts and hashes.

Run only after writers finish. JSON/XML parsed structurally to preserve report integrity.
Values may be synthetic fixtures, but are conservatively removed from deliverables.
"""
import argparse,hashlib,json,pathlib,re,xml.etree.ElementTree as ET
p=argparse.ArgumentParser();p.add_argument('--exclude',action='append',default=[]);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1]/'evidence';changes=[]
key=re.compile(r'\bsk-[A-Za-z0-9_-]{12,}')
pem=re.compile(r'-----BEGIN ([A-Z ]*PRIVATE KEY)-----[\s\S]{0,16384}?-----END \1-----')
header=re.compile(r'-----(?:BEGIN|END) [A-Z ]*PRIVATE KEY-----')
def clean(s,c):
 for name,rx in [('pem',pem),('private_key_header',header),('api_key_shape',key)]:
  s,n=rx.subn('[REDACTED_CREDENTIAL_SHAPED_TEST_VALUE]',s);c[name]=c.get(name,0)+n
 return s
def walk(o,c):
 if isinstance(o,str):return clean(o,c)
 if isinstance(o,list):return [walk(x,c) for x in o]
 if isinstance(o,dict):return {k:walk(v,c) for k,v in o.items()}
 return o
for f in sorted(root.glob('tests-*/**/*')):
 if not f.is_file() or f.suffix not in ['.log','.txt','.json','.xml']:continue
 if any(x in f.parts for x in a.exclude):continue
 data=f.read_bytes()
 try:s=data.decode('utf-8')
 except UnicodeDecodeError:continue
 if not(key.search(s) or header.search(s)):continue
 c={}
 if f.suffix=='.xml':
  tree=ET.fromstring(s)
  for e in tree.iter():
   if e.text:e.text=clean(e.text,c)
   if e.tail:e.tail=clean(e.tail,c)
   for k in list(e.attrib):e.attrib[k]=clean(e.attrib[k],c)
  out=ET.tostring(tree,encoding='unicode',xml_declaration=True)
 elif f.suffix=='.json':out=json.dumps(walk(json.loads(s),c),ensure_ascii=False,indent=2)+'\n'
 else:out=clean(s,c)
 if sum(c.values()):
  f.write_text(out);changes.append({'file':str(f.relative_to(root)),'matches':c,'sha256_before':hashlib.sha256(data).hexdigest(),'sha256_after':hashlib.sha256(out.encode()).hexdigest()})
manifest=root/'tests-redaction-manifest.json';previous=json.loads(manifest.read_text()) if manifest.exists() else {'note':'Credential-shaped values conservatively redacted after execution; they may be synthetic test fixtures. No matched values retained here.','changes':[]}
previous['changes'].extend(changes);manifest.write_text(json.dumps(previous,indent=2)+'\n');print(json.dumps({'files_redacted':len(changes),'matches':sum(sum(x['matches'].values()) for x in changes)}))
