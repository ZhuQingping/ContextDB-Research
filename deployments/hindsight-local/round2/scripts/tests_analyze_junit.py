#!/usr/bin/env python3
"""Extract exact failures/skip reasons, preserving original reports."""
import argparse,collections,json,pathlib,xml.etree.ElementTree as E
p=argparse.ArgumentParser();p.add_argument('junit');a=p.parse_args();path=pathlib.Path(a.junit)
r=E.parse(path).getroot();failed=[];skipped=collections.Counter()
for t in r.iter('testcase'):
 for tag in ['failure','error']:
  item=t.find(tag)
  if item is not None: failed.append({'test':t.attrib.get('classname','')+'::'+t.attrib.get('name',''),'kind':tag,'message':item.attrib.get('message',''),'trace':item.text})
 item=t.find('skipped')
 if item is not None:skipped[item.attrib.get('message','')]+=1
out={'failures':failed,'skip_reasons':dict(skipped)}
(path.parent/'failure-analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for item in failed:print(item['test'],item['kind'],item['message'][:800])
print('SKIP_REASONS',json.dumps(skipped,ensure_ascii=False))
