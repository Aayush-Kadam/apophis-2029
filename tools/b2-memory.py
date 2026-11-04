from pathlib import Path
import argparse,json,time,psutil,datetime
ap=argparse.ArgumentParser();ap.add_argument('--profile',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();e=Path(a.out);profile=Path(a.profile).resolve();root=None
for attempt in range(100):
 for p in psutil.process_iter(['name','cmdline']):
  try:
   cmd=p.info['cmdline'] or []
   if 'chrome' not in (p.info['name'] or '').lower() or any(x.startswith('--type=') for x in cmd):continue
   if any(x.startswith('--user-data-dir=') and Path(x.split('=',1)[1]).resolve()==profile for x in cmd):root=p;break
  except (psutil.Error,OSError):pass
 if root:break
 time.sleep(.1)
if not root:raise RuntimeError('Dedicated Chrome root not found; memory run invalid')
(e/'process-selection.json').write_text(json.dumps({'root_pid':root.pid,'profile':str(profile),'command':root.cmdline(),'measurement':'sum dedicated Chrome root plus descendants; WS can duplicate shared resident pages; private commitment is not resident; USS excludes shared pages; no GPU VRAM measurement'},indent=2));start=time.monotonic();low=0;count=0
with (e/'memory.jsonl').open('w') as stream:
 while time.monotonic()-start<1200 and not (e/'STOP_MEMORY').exists():
  details=[]
  try:procs=[root,*root.children(recursive=True)]
  except psutil.Error:break
  for p in procs:
   try:
    mi=p.memory_full_info();cmd=p.cmdline();details.append({'pid':p.pid,'role':next((x.split('=',1)[1] for x in cmd if x.startswith('--type=')),'browser'),'working_set':mi.rss,'private_commit':mi.private,'uss':mi.uss,'cpu_s':sum(p.cpu_times()[:2])})
   except psutil.Error:pass
  try:phase=(e/'phase.txt').read_text().strip() or 'transition'
  except OSError:phase='transition'
  row={'elapsed_s':time.monotonic()-start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':phase,'available_ram':psutil.virtual_memory().available,'processes':details,**{k:sum(d[k] for d in details) for k in ['working_set','private_commit','uss','cpu_s']}};stream.write(json.dumps(row)+'\n');stream.flush();count+=1;low=low+1 if row['available_ram']<512*1048576 else 0
  if low>=3:(e/'MEMORY_GUARD_STOP').write_text('Three samples below512MiB available');break
  time.sleep(2)
(e/'memory-end.json').write_text(json.dumps({'samples':count,'duration_s':time.monotonic()-start,'headroom_guard':low>=3},indent=2))
