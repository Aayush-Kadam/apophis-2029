"""Regression checks for the confirmed defect. All real holdouts remain unchanged."""
import copy
import json
import numpy as np
import pytest
from astropy.time import Time, TimeDelta
from scipy.interpolate import CubicHermiteSpline
from science.engine import (ROOT, SNAPSHOT, ANALYSIS, cached, parse_vectors,
    parse_vector_epochs, Trajectory, decimal_jd)

def fixture(name):
    data=cached(name)
    return parse_vectors(data)[0], parse_vector_epochs(data)

def test_all_source_epochs_retain_calendar_precision():
    states,epochs=fixture('fine-uniform')
    elapsed=(epochs-epochs[0]).to_value('sec')
    np.testing.assert_allclose(elapsed,np.arange(len(epochs))*10,atol=2e-11,rtol=0)
    original=(states[:,0]-states[0,0])*86400
    assert np.max(abs(original-elapsed)) > 0.00005

def test_previously_failing_observations_and_threshold_preserved():
    states,epochs=fixture('fine-uniform')
    hold,hold_epochs=fixture('holdout-uniform')
    original=Trajectory(states)
    q_old=(hold[:,0]-original.epoch)*86400
    original_error=np.max(np.linalg.norm(original.evaluate(q_old)[1]-hold[:,4:],axis=1))
    baseline=json.loads((SNAPSHOT/'derived/results.json').read_text())
    assert original_error == baseline['holdout']['max_velocity_kms']
    bounds=json.loads((ROOT/'data/acceptance.json').read_text())
    assert bounds['holdout_velocity_kms']==0.00002
    assert original_error > bounds['holdout_velocity_kms']
    corrected=Trajectory(states,epochs)
    q=(hold_epochs-epochs[0]).to_value('sec')
    assert len(q)==240
    assert np.all(np.min(abs(q[:,None]-corrected.t),axis=1)>1)
    r,v=corrected.evaluate(q)
    assert np.max(np.linalg.norm(v-hold[:,4:],axis=1)) <= bounds['holdout_velocity_kms']
    assert np.max(np.linalg.norm(r-hold[:,1:4],axis=1)) <= bounds['holdout_position_km']

def test_calendar_only_does_not_change_vectors():
    states,epochs=fixture('fine-uniform')
    corrected=Trajectory(states,epochs)
    np.testing.assert_array_equal(corrected.states,states)
    r,v=corrected.evaluate(corrected.t)
    np.testing.assert_allclose(r,states[:,1:4],atol=1e-10)
    np.testing.assert_allclose(v,states[:,4:],atol=1e-12)

def test_calendar_day_rollover_and_submillisecond_precision():
    base=Time('2029-04-13T23:59:59.9999',format='isot',scale='tdb')
    other=Time('2029-04-14T00:00:00.0001',format='isot',scale='tdb')
    assert abs((other-base).to_value('sec')-.0002) < 1e-11

@pytest.mark.parametrize('kind',['jd_mismatch','wrong_calendar_scale_label','invalid_calendar','duplicate_calendar'])
def test_reject_inconsistent_source_time_columns(kind):
    d=copy.deepcopy(cached('fine-uniform'))
    rows=d['result'].split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()
    first=rows[0].split(',')
    if kind=='jd_mismatch': first[0]=str(float(first[0])+1/86400)
    elif kind=='wrong_calendar_scale_label':
        d['result']=d['result'].replace('Calendar Date (TDB)','Calendar Date (UT)')
        with pytest.raises(ValueError): parse_vectors(d)
        return
    elif kind=='invalid_calendar': first[1]=' A.D. 2029-Apr-31 19:46:00.0000'
    else:
        # Keep both columns consistent but duplicate an epoch.
        second=rows[1].split(','); second[:2]=first[:2]
        d['result']=d['result'].replace(rows[1],','.join(second))
        with pytest.raises(ValueError): parse_vectors(d)
        return
    d['result']=d['result'].replace(rows[0],','.join(first))
    with pytest.raises(ValueError): parse_vectors(d)

@pytest.mark.parametrize('kind',['utc','wrong_length','offset'])
def test_precise_axis_contract(kind):
    states,epochs=fixture('fine-uniform')
    if kind=='utc': epochs=epochs.utc
    elif kind=='wrong_length': epochs=epochs[:-1]
    else: epochs=epochs+TimeDelta(1,format='sec')
    with pytest.raises(ValueError): Trajectory(states,epochs)

def test_decimal_cad_epoch_keeps_source_precision():
    t=decimal_jd('2462240.407091969')
    expected=Time(2462240., .407091969, format='jd',scale='tdb')
    assert abs((t-expected).to_value('sec')) < 1e-10

def test_event_epoch_roundtrip_and_time_reference():
    result=json.loads((ANALYSIS/'derived/results.json').read_text())
    e=result['event']; cad=result['cad']
    event=Time(e['jd_tdb1'],e['jd_tdb2'],format='jd',scale='tdb')
    source=fixture('fine-uniform')[1][0]
    assert abs((event-source).to_value('sec')-e['seconds'])<1e-10
    reference=Time(cad['jd_tdb1'],cad['jd_tdb2'],format='jd',scale='tdb')
    assert abs((event-reference).to_value('sec')-e['cad_delta_seconds'])<1e-10

def test_independent_hermite_derivative_all_real_holdouts():
    from science.diagnose_timestamps import manual_hermite
    states,epochs=fixture('fine-uniform'); hold,h_epochs=fixture('holdout-uniform')
    traj=Trajectory(states,epochs); q=(h_epochs-epochs[0]).to_value('sec')
    r,v=manual_hermite(traj.t,states[:,1:4],states[:,4:],q)
    actual_r,actual_v=traj.evaluate(q)
    np.testing.assert_allclose(r,actual_r,rtol=0,atol=3e-11)
    np.testing.assert_allclose(v,actual_v,rtol=0,atol=2e-12)

def test_known_analytic_straight_line_minimum():
    # Mandatory master-plan analytic minimum test, previously absent.
    epochs=Time(['2029-04-13T00:00:00','2029-04-13T00:00:10'],format='isot',scale='tdb')
    states=np.array([[epochs[0].jd,-10,10,0,2,0,0],[epochs[1].jd,10,10,0,2,0,0]])
    event=Trajectory(states,epochs).minimum()
    assert abs(event['seconds']-5)<1e-7
    assert abs(event['distance_km']-10)<1e-9

def test_multiple_extrema_within_single_segment():
    # Synthetic cubic has three provable minima where x=0, at t=2,5,8 sec.
    epochs=Time(['2029-04-13T00:00:00','2029-04-13T00:00:10'],format='isot',scale='tdb')
    t=np.array([0.,10.]); x=(t-2)*(t-5)*(t-8); vx=3*t*t-30*t+66
    states=np.column_stack([epochs.jd,x,np.full(2,10.),np.zeros(2),vx,np.zeros((2,2))])
    event=Trajectory(states,epochs).minimum()
    assert event['minima_count']==3
    assert abs(event['distance_km']-10)<1e-8
    assert min(abs(event['seconds']-v) for v in [2,5,8])<1e-7

def test_known_exact_affine_minimum_full_day():
    # Mandatory analytic-motion check with exactly representable day separation.
    # Unlike a 10-second JD fraction, this produces an exactly lower-degree
    # polynomial and exposes a pre-existing coefficient-shape solver defect.
    epochs=Time([2462240.,2462241.],format='jd',scale='tdb')
    speed=20/86400
    states=np.array([[epochs[0].jd,-10,10,0,speed,0,0],
                     [epochs[1].jd,10,10,0,speed,0,0]])
    event=Trajectory(states,epochs).minimum()
    assert abs(event['seconds']-43200)<1e-6
    assert abs(event['distance_km']-10)<1e-9
