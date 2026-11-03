"""Geometric Earth-centered reconstruction; no orbit propagation or risk prediction."""
import csv
import hashlib
import json
import re
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.optimize import brentq, minimize_scalar
from astropy.time import Time, TimeDelta
from decimal import Decimal
from astropy.utils import iers

iers.conf.auto_download = False
AU_KM = 149597870.7
EARTH_RADIUS_KM = 6371.0
ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'data' / 'snapshot-2026-11-03'
ANALYSIS = ROOT / 'data' / 'analysis-g0-r2'

class NonUniqueMinimumError(ValueError):
    """A constant-range interval attains the global minimum at infinitely many times."""

def decimal_jd(value):
    """Keep the precision of a source JD string; never round the large sum first."""
    value = Decimal(str(value))
    whole = int(value)
    return Time(float(whole), float(value-whole), format='jd', scale='tdb')

def parse_vector_epochs(data):
    """Retain the source fractional calendar TDB epochs, not rounded JD floats."""
    months = {m: f'{i:02d}' for i,m in enumerate(
        ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], 1)}
    text = data['result']
    if text.count('$$SOE') != 1 or text.count('$$EOE') != 1:
        raise ValueError('Invalid vector delimiters')
    strings, printed_jd = [], []
    for row in csv.reader(text.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()):
        match = re.fullmatch(r'\s*A\.D\. (\d{4})-([A-Za-z]{3})-(\d{2}) (\d{2}:\d{2}:\d{2}\.\d+)\s*', row[1])
        if not match or match[2] not in months:
            raise ValueError('Unsupported fractional TDB calendar epoch')
        year,month,day,clock = match.groups()
        strings.append(f'{year}-{months[month]}-{day}T{clock}')
        printed_jd.append(decimal_jd(row[0].strip()))
    epochs = Time(strings, format='isot', scale='tdb')
    # 0.2 ms exceeds the combined finite printed resolutions: calendar 0.1 ms,
    # JD 0.0864 ms plus binary64 JD ULP ~0.0403 ms; this is a consistency guard,
    # not a change to any scientific acceptance tolerance.
    mismatch = np.abs((Time(printed_jd)-epochs).to_value('sec'))
    if not np.isfinite(mismatch).all() or np.any(mismatch > 0.0002):
        raise ValueError('Source calendar TDB and JD columns disagree')
    if len(epochs) < 2 or np.any(np.diff((epochs-epochs[0]).to_value('sec')) <= 0):
        raise ValueError('Calendar epochs must be unique and increasing')
    return epochs

def cached(name, base=SNAPSHOT):
    payload = (base / 'raw' / (name + '.json')).read_bytes()
    meta = json.loads((base / 'manifests' / (name + '.json')).read_text())
    if hashlib.sha256(payload).hexdigest() != meta['sha256']:
        raise ValueError('Raw checksum mismatch')
    data = json.loads(payload)
    from .acquire import validate_response
    service = 'horizons' if name not in ('cad', 'sbdb') else name
    validate_response(data, service)
    return data

def validate_states(states):
    s = np.array(states, dtype=np.float64, copy=True)
    if s.ndim != 2 or s.shape[1] != 7 or len(s) < 2:
        raise ValueError('Need at least two [JD_TDB,x,y,z,vx,vy,vz] rows')
    if not np.isfinite(s).all() or not np.all(np.diff(s[:, 0]) > 0):
        raise ValueError('States must be finite, unique and strictly increasing')
    ranges = np.linalg.norm(s[:, 1:4], axis=1)
    speeds = np.linalg.norm(s[:, 4:7], axis=1)
    if np.any(ranges <= 0) or np.any(ranges > 1e9) or np.any(speeds > 200):
        raise ValueError('Implausible KM-S state values')
    s.setflags(write=False)
    return s

def parse_vectors(data):
    text = data.get('result', '')
    header = text.split('$$SOE')[0]
    requirements = [r'Target body name:\s*99942 Apophis', r'Center body name:\s*Earth \(399\)',
                    r'Center-site name:\s*BODY CENTER', r'Output units\s*:\s*KM-S',
                    r'Output type\s*:\s*GEOMETRIC cartesian states', r'Reference frame\s*:\s*ICRF',
                    r'Output format\s*:\s*2 \(position and velocity\)', r'Calendar Date \(TDB\)']
    if not all(re.search(pattern, header) for pattern in requirements):
        raise ValueError('Unverified identity/frame/units/time contract')
    if text.count('$$SOE') != 1 or text.count('$$EOE') != 1:
        raise ValueError('Invalid vector delimiters')
    rows = []
    for row in csv.reader(text.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()):
        if len(row) != 9 or row[-1].strip():
            raise ValueError('Unexpected vector table columns')
        rows.append([float(row[0]), *[float(x) for x in row[2:8]]])
    orbit = re.search(r'Target body name:.*?\{source: JPL#(\d+)\}', header)
    if orbit is None:
        raise ValueError('Missing JPL orbit identity')
    parse_vector_epochs(data)
    return validate_states(rows), {'orbit_id': orbit.group(1), 'target_designation': '99942',
        'center': '500@399', 'reference_system': 'ICRF', 'reference_plane': 'FRAME',
        'correction': 'NONE', 'time_scale': 'TDB', 'units': 'KM-S'}

def parse_cad(data):
    fields = data.get('fields', [])
    required = {'des', 'orbit_id', 'jd', 'dist', 'dist_min', 'dist_max', 'v_rel', 'v_inf', 't_sigma_f'}
    if len(fields) != len(set(fields)) or not required.issubset(fields):
        raise ValueError('Missing/duplicate CAD fields')
    records = data.get('data', [])
    if int(data.get('count', -1)) != 1 or len(records) != 1 or len(records[0]) != len(fields):
        raise ValueError('Expected exactly one encounter')
    record = dict(zip(fields, records[0]))
    if record['des'] != '99942':
        raise ValueError('Wrong CAD target')
    exact_jd = decimal_jd(record['jd'])
    record['jd_tdb1'], record['jd_tdb2'] = float(exact_jd.jd1), float(exact_jd.jd2)
    for key in ('jd', 'dist', 'dist_min', 'dist_max', 'v_rel', 'v_inf'):
        record[key] = float(record[key])
        if not np.isfinite(record[key]) or record[key] <= 0:
            raise ValueError('Invalid CAD value')
    if not 2462238.5 <= record['jd'] <= 2462241.5:
        raise ValueError('Wrong encounter date')
    if not record['dist_min'] <= record['dist'] <= record['dist_max']:
        raise ValueError('Invalid uncertainty bounds')
    return record

class Trajectory:
    def __init__(self, states, epochs=None):
        self.states = validate_states(states)
        self.epoch = self.states[0, 0]
        if epochs is None:
            self.epoch_tdb = Time(self.epoch, format='jd', scale='tdb')
            self.t = (self.states[:, 0] - self.epoch) * 86400.0
        else:
            if not isinstance(epochs, Time) or epochs.scale != 'tdb' or epochs.shape != (len(self.states),):
                raise ValueError('Explicit epochs must be matching TDB Time values')
            if np.any(abs((epochs-Time(self.states[:,0], format='jd',scale='tdb')).to_value('sec')) > 0.0002):
                raise ValueError('State and precise epochs disagree')
            self.epoch_tdb = epochs[0]
            self.t = (epochs-self.epoch_tdb).to_value('sec')
            if not np.isfinite(self.t).all() or not np.all(np.diff(self.t) > 0):
                raise ValueError('Precise epoch axis must increase')
        self.spline = CubicHermiteSpline(self.t, self.states[:, 1:4], self.states[:, 4:7], extrapolate=False)

    def evaluate(self, seconds):
        q = np.asarray(seconds)
        if not np.isfinite(q).all() or np.any(q < self.t[0]) or np.any(q > self.t[-1]):
            raise ValueError('Time outside frozen ephemeris')
        return self.spline(q), self.spline(q, 1)

    def radial(self, seconds):
        r, v = self.evaluate(seconds)
        return float(np.dot(r, v))

    def minimum(self, *, require_interior=True):
        """Find a global in-window minimum; encounter mode requires a bracketed interior event.

        With require_interior=False, boundary minima are returned explicitly.
        Constant-range global minima raise NonUniqueMinimumError. Multiple isolated
        equal minima return the earliest with a non-unique diagnostic.
        """
        # Inspect every polynomial segment for every real stationary point,
        # including more than one extremum inside a single source interval.
        candidates = []
        flat_intervals = []
        for i, width in enumerate(np.diff(self.t)):
            # Work in dimensionless u in [0,1] to condition polynomial roots.
            p = self.spline.c[:, i, :][::-1] * (width ** np.arange(4))[:, None]
            derivative = np.zeros(6)
            for axis in range(3):
                derivative = np.polynomial.polynomial.polyadd(derivative,
                    np.polynomial.polynomial.polymul(p[:, axis], np.polynomial.polynomial.polyder(p[:, axis])))
            if np.all(derivative == 0):
                flat_intervals.append((float(np.linalg.norm(self.evaluate(self.t[i])[0])), i))
                continue
            roots = np.polynomial.polynomial.polyroots(derivative)
            for u in roots:
                if abs(u.imag) < 1e-8 and -1e-10 <= u.real <= 1 + 1e-10:
                    x = self.t[i] + np.clip(u.real, 0, 1) * width
                    eps = min(width * 1e-3, 0.1)
                    # A true minimum can lie exactly on a shared source knot.
                    left, right = max(self.t[0], x-eps), min(self.t[-1], x+eps)
                    if self.radial(left) < 0 < self.radial(right):
                        x = brentq(self.radial, left, right, xtol=1e-8)
                        r, _ = self.evaluate(x)
                        if not any(abs(x-old[1]) <= 1e-6 for old in candidates):
                            candidates.append((float(np.linalg.norm(r)), float(x), i))
        endpoints = [(float(np.linalg.norm(self.evaluate(x)[0])), float(x), i)
                     for x,i in [(self.t[0],0), (self.t[-1],len(self.t)-2)]]
        all_candidates = candidates + endpoints
        global_distance = min(item[0] for item in all_candidates)
        roundoff = 16*np.finfo(float).eps*max(1., global_distance)
        if any(abs(distance-global_distance) <= roundoff for distance,_ in flat_intervals):
            raise NonUniqueMinimumError('Constant-range global minimum has no unique timestamp')
        if not candidates and require_interior:
            raise ValueError('No bracketed local minimum in ephemeris')
        selected = candidates if require_interior else all_candidates
        best_distance = min(item[0] for item in selected)
        tied = [item for item in selected if abs(item[0]-best_distance) <= roundoff]
        distance, t, i = min(tied, key=lambda item: item[1])
        if require_interior and global_distance < distance-roundoff:
            raise ValueError('Global minimum is at window endpoint')
        r, v = self.evaluate(t)
        cross = minimize_scalar(lambda x: float(np.dot(self.evaluate(x)[0], self.evaluate(x)[0])),
                                bounds=(self.t[i], self.t[i+1]), method='bounded', options={'xatol': 1e-7})
        if not cross.success:
            raise ValueError('Independent minimization failed')
        cross_time = float(cross.x)
        boundary = t == self.t[0] or t == self.t[-1]
        if boundary:
            # A bounded scalar optimizer need not evaluate the exact endpoints.
            cross_time = min([cross_time, self.t[i], self.t[i+1]],
                key=lambda q: float(np.dot(self.evaluate(q)[0], self.evaluate(q)[0])))
        event_epoch = self.epoch_tdb + TimeDelta(t, format='sec')
        return {'jd_tdb': float(event_epoch.jd), 'jd_tdb1': float(event_epoch.jd1),
                'jd_tdb2': float(event_epoch.jd2), 'seconds': t,
                'distance_km': distance, 'speed_kms': float(np.linalg.norm(v)),
                'approx_altitude_km': distance-EARTH_RADIUS_KM,
                'range_rate_kms': float(np.dot(r, v)/distance) if distance else None,
                'minima_count': len(candidates), 'crosscheck_delta_seconds': float(cross_time-t),
                'minimum_kind': 'boundary' if boundary else 'interior',
                'unique_within_window': len(tied)==1, 'tied_minima_count': len(tied),
                'position_km': r.tolist(), 'velocity_kms': v.tolist()}

def time_labels(jd):
    t = jd if isinstance(jd, Time) else Time(jd, format='jd', scale='tdb')
    utc = t.utc
    from datetime import timedelta
    return {'utc': utc.isot + 'Z', 'ist': (utc.to_datetime() + timedelta(hours=5, minutes=30)).isoformat()+'+05:30',
            'caveat': 'Future UTC uses the installed leap-second table; later leap seconds could change this display.'}

def canonical_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()
