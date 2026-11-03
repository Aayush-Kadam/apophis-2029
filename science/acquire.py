"""Sequential, bounded JPL acquisition. Contact is supplied at runtime, never exported."""
import argparse
import datetime as dt
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'data' / 'snapshot-2026-11-03'
ENDPOINTS = {'horizons': 'https://ssd.jpl.nasa.gov/api/horizons.api',
             'cad': 'https://ssd-api.jpl.nasa.gov/cad.api',
             'sbdb': 'https://ssd-api.jpl.nasa.gov/sbdb.api'}
VERSIONS = {'horizons': ('1.2', '1.3'), 'cad': ('1.5',), 'sbdb': ('1.3',)}

def validate_response(result, service):
    if result.get('error') or result.get('code'):
        raise ValueError('JPL application error: ' + str(result))
    if result.get('signature', {}).get('version') not in VERSIONS[service]:
        raise ValueError('Unreviewed API version')
    if service == 'horizons' and ('$$SOE' not in result.get('result', '') or '$$EOE' not in result.get('result', '')):
        raise ValueError('No vector table returned')

def fetch(name, service, params, contact, max_attempts=3):
    if max_attempts not in (1, 2, 3):
        raise ValueError('Request attempts must be bounded between one and three')
    raw = SNAPSHOT / 'raw' / (name + '.json')
    meta = SNAPSHOT / 'manifests' / (name + '.json')
    raw.parent.mkdir(parents=True, exist_ok=True)
    meta.parent.mkdir(parents=True, exist_ok=True)
    if raw.exists() or meta.exists():
        if not (raw.exists() and meta.exists()):
            raise ValueError('Incomplete immutable cache: ' + name)
        info = json.loads(meta.read_text())
        payload = raw.read_bytes()
        if info['sha256'] != hashlib.sha256(payload).hexdigest() or info['parameters'] != params:
            raise ValueError('Cache hash/parameters mismatch: ' + name)
        print('CACHE', name, len(payload), flush=True)
        result = json.loads(payload)
        validate_response(result, service)
        return result
    url = ENDPOINTS[service] + '?' + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={'User-Agent': f'ApophisNearMissEngine/0.1.2 (contact: {contact})'})
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read(8_000_001)
                if len(payload) > 8_000_000:
                    raise ValueError('Response exceeds bounded size')
                info = {'endpoint': ENDPOINTS[service], 'parameters': params,
                        'retrieved_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                        'http_status': response.status, 'response_headers': dict(response.headers),
                        'sha256': hashlib.sha256(payload).hexdigest(), 'snapshot_id': SNAPSHOT.name}
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == max_attempts - 1:
                raise
            time.sleep(2 ** (attempt + 1))
        except (urllib.error.URLError, TimeoutError):
            if attempt == max_attempts - 1:
                raise
            time.sleep(2 ** (attempt + 1))
    # Preserve authentic response even when application-level validation fails.
    raw.write_bytes(payload)
    result = json.loads(payload)
    info['api_signature'] = result.get('signature')
    meta.write_text(json.dumps(info, indent=2) + '\n')
    validate_response(result, service)
    print('FETCH', name, len(payload), info['sha256'], flush=True)
    return result

def vector_params(start, stop, step):
    return {'format': 'json', **{k: "'" + v + "'" for k, v in {
        'COMMAND': '99942;', 'OBJ_DATA': 'YES', 'MAKE_EPHEM': 'YES',
        'EPHEM_TYPE': 'VECTORS', 'CENTER': '500@399', 'REF_PLANE': 'FRAME',
        'REF_SYSTEM': 'ICRF', 'VEC_CORR': 'NONE', 'OUT_UNITS': 'KM-S',
        'VEC_TABLE': '2', 'TIME_TYPE': 'TDB', 'TIME_DIGITS': 'FRACSEC',
        'CSV_FORMAT': 'YES', 'START_TIME': start, 'STOP_TIME': stop,
        'STEP_SIZE': step}.items()}}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--contact', required=True)
    p.add_argument('--fine', action='store_true')
    a = p.parse_args()
    if a.fine:
        fetch('fine-uniform', 'horizons', vector_params('2029-Apr-13 19:46', '2029-Apr-13 23:46', '1440'), a.contact)
        # Offset seven seconds from all fine knots, spaced irregularly through event.
        fetch('holdout-uniform', 'horizons', vector_params('2029-Apr-13 19:46:07', '2029-Apr-13 23:45:07', '239'), a.contact)
    else:
        fetch('coarse-numbered', 'horizons', vector_params('2029-Apr-12', '2029-Apr-15', '5 m'), a.contact)
        fetch('cad', 'cad', {'des': '99942', 'body': 'Earth', 'date-min': '2029-04-12',
              'date-max': '2029-04-15', 'dist-max': '0.01', 'fullname': 'true'}, a.contact)
        fetch('sbdb', 'sbdb', {'des': '99942', 'full-prec': 'true', 'phys-par': 'true'}, a.contact)

if __name__ == '__main__':
    main()
