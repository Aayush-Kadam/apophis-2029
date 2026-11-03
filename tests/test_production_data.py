import copy
import hashlib
import json
from pathlib import Path
import shutil
import urllib.error
import pytest
import numpy as np
from astropy.time import TimeDelta
from science import acquire
from science.engine import SNAPSHOT, parse_vector_epochs, cached
from science.snapshot import load_snapshot, check_cadence
from science.export import export_bundle, verify_bundle

def test_complete_snapshot_contract():
    s=load_snapshot()
    assert [len(x.states) for x in [s.coarse,s.fine,s.holdout]]==[865,1441,240]
    assert s.cad['orbit_id']=='220'

@pytest.mark.parametrize('kind',['missing_row','shifted_grid','wrong_count'])
def test_cadence_gaps_rejected(kind):
    epochs=parse_vector_epochs(cached('fine-uniform'))
    params=json.loads((SNAPSHOT/'manifests/fine-uniform.json').read_text())['parameters']
    if kind=='missing_row': epochs=epochs[np.arange(len(epochs))!=100]
    elif kind=='shifted_grid': epochs=epochs+TimeDelta(.1,format='sec')
    else: params=dict(params); params['STEP_SIZE']="'1000'"
    with pytest.raises(ValueError,match='missing, gapped'): check_cadence(epochs,params)

def test_request_contract_tamper(tmp_path):
    shutil.copytree(SNAPSHOT,tmp_path/'snapshot')
    path=tmp_path/'snapshot/manifests/fine-uniform.json'
    d=json.loads(path.read_text()); d['parameters']['CENTER']="'500@10'"
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='contract mismatch'): load_snapshot(tmp_path/'snapshot')

def test_export_deterministic_and_tamper_rejected(tmp_path):
    a=tmp_path/'a'; b=tmp_path/'b'
    assert export_bundle(a)==export_bundle(b)
    assert verify_bundle(a)['orbit_id']=='220'
    (a/'encounter.json').write_text('{}')
    with pytest.raises(ValueError,match='checksum'): verify_bundle(a)

@pytest.mark.parametrize('failure',['429','503','timeout'])
def test_bounded_network_retries_without_actual_network(monkeypatch,tmp_path,failure):
    monkeypatch.setattr(acquire,'SNAPSHOT',tmp_path)
    calls=[]; sleeps=[]
    def fake(request,timeout):
        calls.append(timeout)
        assert 'SyntheticOfflineTest/1.0' in request.get_header('User-agent')
        if failure=='timeout': raise TimeoutError('simulated')
        raise urllib.error.HTTPError(request.full_url,int(failure),'simulated',{},None)
    monkeypatch.setattr(acquire.urllib.request,'urlopen',fake)
    monkeypatch.setattr(acquire.time,'sleep',sleeps.append)
    with pytest.raises((urllib.error.HTTPError,TimeoutError)):
        # This value is a labeled mock contact marker, intercepted before networking.
        acquire.fetch('mock','cad',{'des':'99942'},'SyntheticOfflineTest/1.0')
    assert calls==[45,45,45] and sleeps==[2,4]
    assert not (tmp_path/'raw/mock.json').exists()

def test_cache_reuse_does_not_network(monkeypatch):
    def forbidden(*a,**k): raise AssertionError('Unexpected request')
    monkeypatch.setattr(acquire.urllib.request,'urlopen',forbidden)
    params=json.loads((SNAPSHOT/'manifests/cad.json').read_text())['parameters']
    assert acquire.fetch('cad','cad',params,'UnusedOfflineMarker')['count']==1

@pytest.mark.parametrize('kind',['missing_markers','truncated_row','missing_header'])
def test_malformed_vector_text_rejected(kind):
    from science.engine import parse_vectors
    d=copy.deepcopy(cached('fine-uniform'))
    if kind=='missing_markers': d['result']=d['result'].replace('$$EOE','')
    elif kind=='missing_header': d['result']=d['result'].replace('Output units','Omitted units')
    else:
        rows=d['result'].split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()
        d['result']=d['result'].replace(rows[0],','.join(rows[0].split(',')[:5]))
    with pytest.raises(ValueError): parse_vectors(d)
