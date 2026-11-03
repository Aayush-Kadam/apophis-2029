"""Original Windows-serving helper tests; synthetic local files are not science data."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

path=Path(__file__).resolve().parents[1]/'launchers/windows/launch_apophis.py'
spec=importlib.util.spec_from_file_location('apophis_static_launcher',path)
launcher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

def valid_layout(tmp_path):
    (tmp_path/'index.html').write_text('<title>Synthetic launcher fixture</title>')
    (tmp_path/'snapshots').mkdir()
    payload=b'{"fixture":"synthetic launcher test only"}'
    (tmp_path/'snapshots/encounter.json').write_bytes(payload)
    (tmp_path/'snapshots/manifest.json').write_text(json.dumps({'files':{'encounter.json':hashlib.sha256(payload).hexdigest()}}))
    return tmp_path

def test_launcher_directory_is_own_file_parent():
    assert launcher.APP_DIR==path.parent

def test_launcher_accepts_complete_matching_layout(tmp_path,monkeypatch):
    directory=tmp_path/'app';directory.mkdir();valid_layout(directory)
    other=tmp_path/'unrelated';other.mkdir();monkeypatch.chdir(other)
    launcher.verify_application(directory)

def test_launcher_rejects_wrong_folder(tmp_path):
    with pytest.raises(ValueError,match='index.html is missing'):launcher.verify_application(tmp_path)

def test_launcher_rejects_corrupted_snapshot(tmp_path):
    directory=valid_layout(tmp_path)
    (directory/'snapshots/encounter.json').write_text('tampered synthetic fixture')
    with pytest.raises(ValueError,match='hash mismatch'):launcher.verify_application(directory)

def test_launcher_rejects_missing_snapshot(tmp_path):
    directory=valid_layout(tmp_path)
    (directory/'snapshots/encounter.json').unlink()
    with pytest.raises(FileNotFoundError):launcher.verify_application(directory)

def test_launcher_rejects_an_occupied_listening_port():
    from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
    with ThreadingHTTPServer(('127.0.0.1', 0), SimpleHTTPRequestHandler) as occupied:
        with pytest.raises(OSError):
            launcher.LocalHTTPServer(occupied.server_address, SimpleHTTPRequestHandler)

def test_launcher_can_restart_after_close():
    from http.server import SimpleHTTPRequestHandler
    with launcher.LocalHTTPServer(('127.0.0.1', 0), SimpleHTTPRequestHandler) as first:
        address = first.server_address
    with launcher.LocalHTTPServer(address, SimpleHTTPRequestHandler) as restarted:
        assert restarted.server_address == address
