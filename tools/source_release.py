# Copyright 2026 Aayush Kadam
# SPDX-License-Identifier: Apache-2.0
"""Acquire a NEW private run from official APIs; never replace the validated snapshot."""
import argparse
from datetime import datetime, timezone
from functools import partial
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

SOURCE = Path(__file__).resolve().parents[1]
if str(SOURCE) not in sys.path: sys.path.insert(0, str(SOURCE))

def contact_value(value):
    value = value.strip()
    if not (re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) or re.fullmatch(r'https://[^\s/]+(?:/[^\s]*)?', value)):
        raise ValueError('Supply a real email address or public HTTPS contact URL; no contact is invented.')
    return value

def validate_destination(destination):
    destination = destination.resolve()
    if destination == SOURCE or destination.is_relative_to(SOURCE):
        raise ValueError('Use a separate, new output directory outside this source tree.')
    if destination.exists():
        raise ValueError('Output already exists. Preserve it; choose a new run directory.')
    return destination

def require_supported_orbit(snapshot):
    if snapshot.cad['orbit_id'] != '220':
        raise ValueError('Current source is not orbit 220. No scientific contract or reference is changed; new validation needs authorization.')

def acquire_and_build(destination, contact):
    from science import acquire, engine, run, snapshot, export
    destination=validate_destination(destination);contact=contact_value(contact)
    destination.mkdir(parents=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base=destination/'data'/('source-api-'+stamp)
    acquire.SNAPSHOT=base
    requests=[
        ('coarse-numbered','horizons',acquire.vector_params('2029-Apr-12','2029-Apr-15','5 m')),
        ('cad','cad',{'des':'99942','body':'Earth','date-min':'2029-04-12','date-max':'2029-04-15','dist-max':'0.01','fullname':'true'}),
        ('sbdb','sbdb',{'des':'99942','full-prec':'true','phys-par':'true'}),
        ('fine-uniform','horizons',acquire.vector_params('2029-Apr-13 19:46','2029-Apr-13 23:46','1440')),
        ('holdout-uniform','horizons',acquire.vector_params('2029-Apr-13 19:46:07','2029-Apr-13 23:45:07','239')),
    ]
    summary={'status':'ACQUIRING','snapshot_id':base.name,'policy_url':'https://ssd-api.jpl.nasa.gov/',
        'execution':'At most five sequential HTTP attempts; no automatic retries; version checks; no contact stored.',
        'request_ledger':[], 'request_limit':5,
        'frozen_baseline_replaced':False,'public_redistribution_permission':'NOT ESTABLISHED by acquisition'}
    def record(): (destination/'source-run.json').write_text(json.dumps(summary,indent=2)+'\n')
    record()
    try:
        for index,(name,service,params) in enumerate(requests):
            entry={'ordinal':index+1,'name':name,'service':service,'state':'ATTEMPT_RESERVED',
                   'reserved_utc':datetime.now(timezone.utc).isoformat()}
            summary['request_ledger'].append(entry);record()
            acquire.fetch(name,service,params,contact,max_attempts=1)
            entry['state']='RESPONSE_SAVED';record()
            if index+1<len(requests):time.sleep(1)
        loaded=snapshot.load_snapshot(base);require_supported_orbit(loaded)
        # Redirect I/O only. The original interpolation, solver and acceptance math are unchanged.
        (destination/'data').mkdir(exist_ok=True);shutil.copy2(SOURCE/'data/acceptance.json',destination/'data/acceptance.json')
        (destination/'science').mkdir();shutil.copy2(SOURCE/'science/engine.py',destination/'science/engine.py')
        shutil.copy2(SOURCE/'requirements.lock',destination/'requirements.lock')
        run.ROOT=destination;run.SNAPSHOT=base;run.ANALYSIS=destination/'data/analysis-source';run.cached=partial(engine.cached,base=base)
        results=run.experiment()
        if not all(results['checks'].values()):raise ValueError('Unchanged scientific acceptance failed; no application export approved.')
        export.ROOT=destination;export.ANALYSIS=run.ANALYSIS;export.load_snapshot=partial(snapshot.load_snapshot,base=base)
        output=destination/'frontend-snapshots';manifest=export.export_bundle(output)
        # Exporter's historical default ID is bookkeeping, not reused as a false retrieval identity.
        bundle=json.loads((output/'encounter.json').read_text());bundle['snapshot_id']=base.name
        manifest['snapshot_id']=base.name;manifest['files']['encounter.json']=engine.canonical_write(output/'encounter.json',bundle)
        engine.canonical_write(output/'manifest.json',manifest);export.verify_bundle(output)
        summary.update(status='PASS_NEW_RUN',orbit_id=loaded.cad['orbit_id'],checks=results['checks'],
            source_files={str(f.relative_to(destination)).replace('\\','/'):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in base.rglob('*') if f.is_file()},
            frontend_manifest=manifest,note='New API-derived run, not byte-identical historical evidence. Publishing generated outputs still needs rights clearance.')
        record();return summary
    except Exception as exc:
        summary.update(status='FAILED_CLOSED',error_type=type(exc).__name__,error=str(exc));record();raise

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--contact-env',default='APOPHIS_JPL_CONTACT')
    args=parser.parse_args()
    destination=validate_destination(args.output)
    contact=contact_value(os.environ.get(args.contact_env) or getpass.getpass('JPL contact email/public URL (not saved): '))
    summary=acquire_and_build(destination,contact)
    print(json.dumps({'status':summary['status'],'snapshot_id':summary['snapshot_id'],'orbit_id':summary.get('orbit_id')},indent=2))

if __name__=='__main__':main()
