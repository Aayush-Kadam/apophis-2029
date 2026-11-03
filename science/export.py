"""Deterministic, local-only, checksummed frontend data; no browser JPL requests."""
import hashlib
import json
from pathlib import Path
import numpy as np
from astropy.time import Time
from .engine import ROOT, ANALYSIS, Trajectory, canonical_write
from .snapshot import load_snapshot

DEST = ROOT/'web/public/snapshots'

def export_bundle(destination: Path=DEST) -> dict:
    snapshot=load_snapshot()
    results=json.loads((ANALYSIS/'derived/results.json').read_text())
    expected=json.loads((ROOT/'benchmarks/g0-r2.json').read_text())['results_sha256']
    if hashlib.sha256((ANALYSIS/'derived/results.json').read_bytes()).hexdigest()!=expected:
        raise ValueError('Derived output checksum mismatch')
    if not all(results['checks'].values()): raise ValueError('Unvalidated numerical output')
    base=snapshot.coarse.epochs[0]
    def series(value):
        return np.column_stack([(value.epochs-base).to_value('sec'),value.states[:,1:]]).tolist()
    fine=Trajectory(snapshot.fine.states,snapshot.fine.epochs)
    hold_seconds=(snapshot.holdout.epochs-fine.epoch_tdb).to_value('sec')
    r,v=fine.evaluate(hold_seconds)
    event=results['event']; event_time=Time(event['jd_tdb1'],event['jd_tdb2'],format='jd',scale='tdb')
    provenance={name:{key:info[key] for key in ['endpoint','parameters','retrieved_utc','sha256','api_signature']}
        for name,info in snapshot.source_manifests.items() if name in ['coarse-numbered','fine-uniform','holdout-uniform','cad','sbdb']}
    report={k:v for k,v in results.items() if k!='time_conversion_warnings'}
    bundle={'schema_version':'1.0','snapshot_id':'snapshot-2026-11-03','orbit_id':'220',
        'time_scale':'TDB','frame':'Earth-centered ICRF, FRAME, geometric NONE',
        'units':{'position':'km','velocity':'km/s','elapsed_time':'s'},
        'origin_jd_tdb1':float(base.jd1),'origin_jd_tdb2':float(base.jd2),
        'columns':['elapsed_seconds','x_km','y_km','z_km','vx_kms','vy_kms','vz_kms'],
        'coarse':series(snapshot.coarse),'fine':series(snapshot.fine),
        'event_seconds':float((event_time-base).to_value('sec')),
        'earth_radius_km':6371.,'results':report,'provenance':provenance,
        'validation_fixtures':{'origin':'All 240 genuine independent holdouts; expected values below are interpolated model values, not source vectors.',
            'seconds':(snapshot.holdout.epochs-base).to_value('sec').tolist(),
            'expected_distance_km':np.linalg.norm(r,axis=1).tolist(),
            'expected_speed_kms':np.linalg.norm(v,axis=1).tolist()}}
    destination.mkdir(parents=True,exist_ok=True)
    digest=canonical_write(destination/'encounter.json',bundle)
    manifest={'schema_version':'1.0','snapshot_id':bundle['snapshot_id'],
        'files':{'encounter.json':digest},'science_result_sha256':expected,
        'algorithm_source_sha256':hashlib.sha256((ROOT/'science/engine.py').read_bytes()).hexdigest(),
        'requirements_sha256':hashlib.sha256((ROOT/'requirements.lock').read_bytes()).hexdigest(),
        'note':'Checksums detect corruption relative to this packaged manifest; they are not an independently authenticated source signature.'}
    canonical_write(destination/'manifest.json',manifest)
    return manifest

def verify_bundle(directory: Path=DEST) -> dict:
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest.get('schema_version')!='1.0': raise ValueError('Unsupported manifest schema')
    for name,expected in manifest['files'].items():
        if name!='encounter.json': raise ValueError('Unexpected bundle filename')
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Frontend bundle checksum mismatch')
    return json.loads((directory/'encounter.json').read_text())

if __name__=='__main__': print(json.dumps(export_bundle(),indent=2))
