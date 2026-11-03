"""Synthetic fixtures below are explicitly mathematical tests, never JPL data."""
import copy
import json
import socket
import numpy as np
import pytest
from scipy.optimize import brentq
from science.engine import (ROOT, SNAPSHOT, AU_KM, Trajectory, cached, parse_cad,
                            parse_vectors, validate_states, time_labels, canonical_write)
from science.acquire import validate_response

@pytest.fixture(scope='module')
def result():
    # Same frozen assertions, now applied to the corrected run; baseline is preserved.
    return json.loads((ROOT/'data/analysis-g0-r2/derived/results.json').read_text())

@pytest.fixture(scope='module')
def actual():
    return parse_vectors(cached('fine-uniform'))[0]

def linear_states():
    # Synthetic straight line, impact parameter 10 km, constant speed 2 km/s.
    return np.array([[2451545.0, -20, 10, 0, 2, 0, 0],
                     [2451545.0 + 20/86400, 20, 10, 0, 2, 0, 0]])

@pytest.mark.parametrize('kind', ['nan', 'inf', 'duplicate', 'reverse', 'empty', 'shape', 'units'])
def test_bad_states(kind):
    a = linear_states()
    if kind == 'nan': a[0, 1] = np.nan
    elif kind == 'inf': a[0, 4] = np.inf
    elif kind == 'duplicate': a[1, 0] = a[0, 0]
    elif kind == 'reverse': a = a[::-1]
    elif kind == 'empty': a = np.empty((0, 7))
    elif kind == 'shape': a = np.zeros((2, 6))
    elif kind == 'units': a[0, 4] = 86400
    with pytest.raises(ValueError): validate_states(a)

@pytest.mark.parametrize('old,new', [('ICRF','Ecliptic of J2000.0'), ('KM-S','AU-D'),
    ('GEOMETRIC cartesian states','LT+S'), ('Earth (399)','Sun (10)'),
    ('99942 Apophis','433 Eros'), ('Calendar Date (TDB)','Calendar Date (UT)')])
def test_reject_contract(old, new):
    d = copy.deepcopy(cached('fine-uniform'))
    d['result'] = d['result'].replace(old, new)
    with pytest.raises(ValueError): parse_vectors(d)

@pytest.mark.parametrize('change', ['unknown_version', 'error', 'no_table'])
def test_response_rejection(change):
    d = {'signature': {'version': '1.2'}, 'result': '$$SOE\n$$EOE'}
    if change == 'unknown_version': d['signature']['version'] = '99'
    if change == 'error': d['error'] = 'Bad request'
    if change == 'no_table': d['result'] = 'No matches found.'
    with pytest.raises(ValueError): validate_response(d, 'horizons')

def test_permuted_cad_fields():
    d = copy.deepcopy(cached('cad'))
    expected = parse_cad(d)
    d['fields'] = d['fields'][::-1]
    d['data'][0] = d['data'][0][::-1]
    assert parse_cad(d) == expected

@pytest.mark.parametrize('kind', ['empty', 'missing', 'wrong_target'])
def test_bad_cad(kind):
    d = copy.deepcopy(cached('cad'))
    if kind == 'empty': d['data'] = []; d['count'] = 0
    elif kind == 'missing': d['fields'][0] = 'unknown'
    else: d['data'][0][d['fields'].index('des')] = '433'
    with pytest.raises(ValueError): parse_cad(d)

def test_au_definition():
    assert AU_KM == 149597870.7

def test_day_to_seconds_and_hermite_derivative(actual):
    t = Trajectory(actual)
    assert abs(np.median(np.diff(t.t))-10) < 0.0001
    q = (t.t[100]+t.t[101])/2
    r, v = t.evaluate(q)
    numerical = (t.evaluate(q+0.01)[0]-t.evaluate(q-0.01)[0])/0.02
    assert np.linalg.norm(numerical-v) < 1e-7

def test_cubic_position_velocity_fixture():
    # Synthetic cubic r(t), exactly representable by Hermite.
    t = np.array([0., 86400.])
    u = t/86400
    pos = np.column_stack([100+u**3, 10+u**2, 2+u])
    vel = np.column_stack([3*u*u, 2*u, np.ones(2)])/86400
    traj = Trajectory(np.column_stack([2451545+u, pos, vel]))
    r, v = traj.evaluate(43200)
    np.testing.assert_allclose(r, [100.125,10.25,2.5], atol=1e-10)
    np.testing.assert_allclose(v, np.array([.75,1,1])/86400, atol=1e-12)

def test_knots(actual):
    t = Trajectory(actual)
    r,v = t.evaluate(t.t)
    np.testing.assert_allclose(r, actual[:,1:4], atol=1e-10)
    np.testing.assert_allclose(v, actual[:,4:], atol=1e-12)

def test_no_extrapolation(actual):
    with pytest.raises(ValueError): Trajectory(actual).evaluate(-1)

def test_immutable_coordinates(actual):
    t = Trajectory(actual)
    original = actual.copy()
    r,_ = t.evaluate(10)
    r *= .001
    assert np.array_equal(actual, original)
    assert not t.states.flags.writeable

def test_missing_bracket(actual):
    with pytest.raises(ValueError): Trajectory(actual[:3]).minimum()

def test_local_minimum_and_single_event(result, actual):
    t = Trajectory(actual)
    q = result['event']['seconds']
    assert t.radial(q-1) < 0 < t.radial(q+1)
    assert result['event']['minima_count'] == 1

def test_independent_method(result):
    assert abs(result['event']['crosscheck_delta_seconds']) < .02

def test_altitude_separate(result):
    e = result['event']
    assert e['distance_km']-e['approx_altitude_km'] == 6371

def test_compatible_orbit(result):
    assert result['metadata']['orbit_id'] == result['cad']['orbit_id'] == '220'

def test_tdb_conversion():
    from astropy.time import Time
    jd = 2451545.
    labels = time_labels(jd)
    assert labels['utc'].startswith('2000-01-01T11:58:55.')
    assert labels['ist'].startswith('2000-01-01T17:28:55.')
    t = Time(jd, format='jd', scale='tdb')
    assert abs(t.utc.tdb.jd-jd) < 1e-10

def test_deterministic_export(tmp_path):
    a = canonical_write(tmp_path/'a.json', {'b':2,'a':1})
    b = canonical_write(tmp_path/'b.json', {'a':1,'b':2})
    assert a == b

def test_tamper_detected(tmp_path):
    (tmp_path/'raw').mkdir(); (tmp_path/'manifests').mkdir()
    (tmp_path/'raw/cad.json').write_text('{}')
    (tmp_path/'manifests/cad.json').write_text('{"sha256":"incorrect"}')
    with pytest.raises(ValueError): cached('cad', tmp_path)

def test_offline_cache(monkeypatch):
    def forbidden(*a, **k): raise AssertionError('Unexpected networking')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    assert len(parse_vectors(cached('fine-uniform'))[0]) == 1441

@pytest.mark.parametrize('name', ['g0_cad_distance','g0_cad_time','refined_cad_distance',
    'refined_cad_time','cad_speed','holdout_position','holdout_velocity',
    'convergence_distance','convergence_time','independent_minimizer','stationarity'])
def test_frozen_acceptance(result, name):
    assert result['checks'][name], f'Frozen scientific acceptance failed: {name}'
