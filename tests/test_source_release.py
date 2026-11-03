"""Release workflow guards; fixtures here contain no JPL data."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
path=Path(__file__).resolve().parents[1]/'tools/source_release.py'
spec=importlib.util.spec_from_file_location('source_release',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
@pytest.mark.parametrize('contact',['','invented','missing@','https://'])
def test_invalid_contact_rejected(contact):
    with pytest.raises(ValueError):module.contact_value(contact)
def test_original_tree_cannot_be_destination():
    with pytest.raises(ValueError):module.validate_destination(module.SOURCE/'data/new-run')
def test_existing_destination_not_overwritten(tmp_path):
    with pytest.raises(ValueError):module.validate_destination(tmp_path)
def test_new_destination_accepted(tmp_path):
    assert module.validate_destination(tmp_path/'new')==tmp_path/'new'
def test_changed_orbit_rejected():
    with pytest.raises(ValueError):module.require_supported_orbit(SimpleNamespace(cad={'orbit_id':'221'}))

def test_single_attempt_mode_never_retries(monkeypatch,tmp_path):
    from science import acquire
    import urllib.error
    monkeypatch.setattr(acquire,'SNAPSHOT',tmp_path)
    calls=[]
    def unavailable(request,timeout):
        calls.append(request)
        raise urllib.error.HTTPError(request.full_url,503,'synthetic unavailable',{},None)
    monkeypatch.setattr(acquire.urllib.request,'urlopen',unavailable)
    with pytest.raises(urllib.error.HTTPError):
        acquire.fetch('synthetic','sbdb',{'des':'99942'},'fixture@example.invalid',max_attempts=1)
    assert len(calls)==1
    assert 'ApophisNearMissEngine/0.1.2' in calls[0].get_header('User-agent')
