"""Typed, fail-closed loading of the complete frozen source contract."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
import numpy as np
from astropy.time import Time
from .engine import SNAPSHOT, cached, parse_vectors, parse_vector_epochs, parse_cad

@dataclass(frozen=True)
class VectorSeries:
    states: np.ndarray
    epochs: Time
    metadata: Mapping[str, str]

@dataclass(frozen=True)
class SourceSnapshot:
    coarse: VectorSeries
    fine: VectorSeries
    holdout: VectorSeries
    cad: Mapping
    source_manifests: Mapping

def request_epoch(value: str) -> Time:
    value=value.strip("'")
    for fmt in ('%Y-%b-%d %H:%M:%S','%Y-%b-%d %H:%M','%Y-%b-%d'):
        try: return Time(datetime.strptime(value,fmt).isoformat(),format='isot',scale='tdb')
        except ValueError: pass
    raise ValueError('Unsupported request calendar time')

def check_cadence(epochs: Time, params: Mapping[str,str]) -> None:
    start=request_epoch(params['START_TIME']); stop=request_epoch(params['STOP_TIME'])
    span=float((stop-start).to_value('sec'))
    step=params['STEP_SIZE'].strip("'")
    if step.isdigit():
        count=int(step)+1
        if count<2: raise ValueError('Invalid uniform interval count')
        seconds=span/(count-1)
    else:
        pieces=step.split()
        if len(pieces)!=2 or pieces[1]!='m': raise ValueError('Unreviewed cadence units')
        seconds=float(pieces[0])*60
        if seconds<=0: raise ValueError('Invalid cadence')
        count=round(span/seconds)+1
    actual=(epochs-start).to_value('sec')
    if len(actual)!=count or not np.allclose(actual,np.arange(count)*seconds,rtol=0,atol=.0002):
        raise ValueError('Source samples missing, gapped or outside requested cadence/window')

def load_snapshot(base: Path=SNAPSHOT) -> SourceSnapshot:
    manifests={}
    # Include rejected replies in integrity accounting without accepting them as vectors.
    for path in sorted((base/'manifests').glob('*.json')):
        info=json.loads(path.read_text())
        raw=(base/'raw'/(path.stem+'.json')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=info['sha256']:
            raise ValueError('Source checksum mismatch')
        manifests[path.stem]=info
    expected={'COMMAND':'99942;','EPHEM_TYPE':'VECTORS','CENTER':'500@399',
        'REF_PLANE':'FRAME','REF_SYSTEM':'ICRF','VEC_CORR':'NONE','OUT_UNITS':'KM-S',
        'VEC_TABLE':'2','TIME_TYPE':'TDB','CSV_FORMAT':'YES'}
    vectors=[]
    for name in ['coarse-numbered','fine-uniform','holdout-uniform']:
        info=manifests[name]
        params=info['parameters']
        if info['http_status']!=200 or info['endpoint']!='https://ssd.jpl.nasa.gov/api/horizons.api':
            raise ValueError('Invalid source HTTP/endpoint provenance')
        if any(params.get(k,'').strip("'")!=v for k,v in expected.items()):
            raise ValueError('Request coordinate/time contract mismatch')
        data=cached(name,base)
        if data['signature']['source']!='NASA/JPL Horizons API': raise ValueError('Wrong API provider')
        states,metadata=parse_vectors(data); epochs=parse_vector_epochs(data)
        check_cadence(epochs,params)
        vectors.append(VectorSeries(states,epochs,MappingProxyType(metadata)))
    cad_params=manifests['cad']['parameters']
    if any(cad_params.get(k)!=v for k,v in {'des':'99942','body':'Earth',
        'date-min':'2029-04-12','date-max':'2029-04-15'}.items()):
        raise ValueError('CAD request does not select the encounter/body explicitly')
    cad=parse_cad(cached('cad',base)); sbdb=cached('sbdb',base)
    orbit=cad['orbit_id']
    if sbdb['object']['des']!='99942' or sbdb['orbit']['orbit_id']!=orbit or any(x.metadata['orbit_id']!=orbit for x in vectors):
        raise ValueError('Orbit compatibility LIMITED: source solutions differ')
    return SourceSnapshot(*vectors,MappingProxyType(cad),MappingProxyType(manifests))
