"""Recompute report evidence from a fixed in-memory snapshot; never run inference."""
import sys,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from src import grade
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
items={task:{x['qid']:x for x in json.loads((ROOT/'data'/f'{task}_queries.json').read_text())} for task in ('task1','task2')}
trials=[]; files=[]; mismatch=[]; duplicates=[]; malformed=[]
for p in sorted((ROOT/'runs').rglob('*.jsonl')):
 raw=p.read_bytes(); records=[]
 for i,line in enumerate(raw.splitlines(),1):
  try: records.append(json.loads(line))
  except ValueError: malformed.append([str(p.relative_to(ROOT)),i])
 if not records or records[0].get('type')!='run':continue
 h=records[0]; seen=set(); count=0
 for r in records[1:]:
  if r.get('type')!='trial':continue
  count+=1; key=(r['qid'],r['seed'])
  if key in seen:duplicates.append([str(p),key])
  seen.add(key)
  if h.get('ladder'):continue
  item=items[h['task']][r['qid']]
  g=grade.grade(h['task'],item,r['raw'],h['arm'])
  for k in ('correct','correct_norm','valid','valid_norm','extraction_ok','normalized','error_type','gold'):
   if r.get(k)!=g[k]:mismatch.append([str(p.relative_to(ROOT)),r['qid'],r['seed'],k,r.get(k),g[k]])
  trials.append({**r,**{k:h.get(k) for k in ('model','task','arm','temperature','prompt_version','backend')},'band':item.get('l',item.get('places')),'source':str(p.relative_to(ROOT))})
 files.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'trials':count,'header':h})
def stats(tt):
 good=[t for t in tt if not t['invalid']]; n=len(good); c=sum(t['correct_norm'] for t in good); groups=defaultdict(list)
 for t in good:groups[(t['temperature'],t['qid'])].append(t['normalized'])
 cons=[max(Counter(v).values())/len(v) for v in groups.values()]
 return {'attempts':len(tt),'eligible':n,'correct':c,'strict_correct':sum(t['correct'] for t in good),'accuracy':c/n if n else None,'success_all':c/len(tt) if tt else None,'excluded':len(tt)-n,'truncated':sum(t['truncated'] for t in tt),'missing_final':sum(not t['extraction_ok'] for t in tt),'valid_format':sum(t['valid_norm'] for t in good),'consistency':sum(cons)/len(cons) if cons else None,'errors':dict(Counter(t['error_type'] for t in good)),'mean_output_tokens':sum(t.get('output_tokens',0) or 0 for t in tt)/len(tt),'temps':sorted({t['temperature'] for t in tt}),'seeds':sorted({t['seed'] for t in tt})}
group=defaultdict(list);cells=defaultdict(list);bands=defaultdict(list)
for t in trials:
 key=(t['model'],t['task'],t['arm']);group[key].append(t);cells[key+(t['temperature'],)].append(t);bands[key+(t['band'],)].append(t)
evidence={'snapshot_utc':datetime.now(timezone.utc).isoformat(),'total_trials':len(trials),'files':files,'malformed':malformed,'duplicates':duplicates,'grading_mismatches':mismatch,'summary':{'|'.join(k):stats(v) for k,v in group.items()},'cells':{'|'.join(map(str,k)):stats(v) for k,v in cells.items()},'bands':{'|'.join(map(str,k)):stats(v) for k,v in bands.items()}}
(OUT/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
# Exact raw examples permit audit without trusting an interpretation of model prose.
examples=[]
for key,tt in group.items():
 for correct in (True,False):
  sample=next((t for t in tt if t['temperature']==0 and not t['invalid'] and t['correct_norm']==correct),None)
  if sample:examples.append(sample)
(OUT/'examples.json').write_text(json.dumps(examples,indent=2)+'\n')
print('Snapshot',evidence['snapshot_utc'],'trials',len(trials),'files',len(files),'grading mismatches',len(mismatch),'duplicates',len(duplicates),'malformed',len(malformed))
for k,s in evidence['summary'].items():
 print(k, 'correct',f"{s['correct']}/{s['eligible']}", 'all',s['attempts'],'strict',s['strict_correct'],'excluded',s['excluded'],'format',s['valid_format'],'tokens',round(s['mean_output_tokens'],1))
print('MISMATCHES',mismatch[:8])
