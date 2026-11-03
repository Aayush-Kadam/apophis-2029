"""Explicit mathematical fixtures, independent of JPL; expected policy fixed before runs."""
import numpy as np
import pytest
from astropy.time import Time
import science.engine as engine
from science.engine import Trajectory, NonUniqueMinimumError

EPOCH = 2462240.
DURATION = 86400.

def line(r0, velocity, *, knots=None):
    t=np.array([0.,DURATION] if knots is None else knots)
    epochs=Time(EPOCH,t/86400,format='jd',scale='tdb')
    r0=np.array(r0,dtype=float); velocity=np.array(velocity,dtype=float)
    states=np.column_stack([epochs.jd,r0+t[:,None]*velocity,np.tile(velocity,(len(t),1))])
    return Trajectory(states,epochs)

@pytest.mark.parametrize('rotation', [np.eye(3),
    np.array([[0,0,1],[1,0,0],[0,1,0]]),
    np.array([[.6,-.8,0],[.8,.6,0],[0,0,1]]),
    np.array([[1,0,0],[0,.6,-.8],[0,.8,.6]])])
def test_linear_interior_analytic_reference_orientations(rotation):
    r0=rotation@np.array([-10.,10.,0.]); velocity=rotation@np.array([20/DURATION,0,0])
    assert np.dot(velocity,velocity)>0
    analytic=-np.dot(r0,velocity)/np.dot(velocity,velocity)
    expected=np.linalg.norm(r0+analytic*velocity)
    traj=line(r0,velocity); e=traj.minimum()
    assert 0 < analytic < DURATION
    assert abs(e['seconds']-analytic)<1e-6
    assert abs(e['distance_km']-expected)<1e-10
    assert abs(e['range_rate_kms'])<1e-12
    assert e['minimum_kind']=='interior' and e['unique_within_window']
    assert traj.radial(analytic-1)<0<traj.radial(analytic+1)

@pytest.mark.parametrize('r0,vx,expected', [
    ([0,10,0],10/DURATION,0),
    ([-10,10,0],10/DURATION,DURATION),
    ([10,10,0],20/DURATION,0),
    ([-30,10,0],20/DURATION,DURATION)])
def test_boundary_and_outside_unconstrained_minimum(r0,vx,expected):
    traj=line(r0,[vx,0,0])
    theoretical=-np.dot(r0,[vx,0,0])/(vx*vx)
    assert abs(np.clip(theoretical,0,DURATION)-expected)<1e-6
    e=traj.minimum(require_interior=False)
    assert e['seconds']==expected
    assert e['minimum_kind']=='boundary'
    assert e['unique_within_window']
    assert abs(e['distance_km']-np.linalg.norm(np.array(r0)+[vx*expected,0,0]))<1e-10
    with pytest.raises(ValueError,match='No bracketed|endpoint'): traj.minimum()

def test_source_knot_minimum_deduplicated():
    traj=line([-10,10,0],[20/DURATION,0,0],knots=[0,DURATION/2,DURATION])
    e=traj.minimum()
    assert abs(e['seconds']-DURATION/2)<1e-6
    assert e['minima_count']==1

@pytest.mark.parametrize('require_interior',[True,False])
def test_stationary_has_no_unique_time(require_interior):
    with pytest.raises(NonUniqueMinimumError,match='no unique timestamp'):
        line([10,20,30],[0,0,0]).minimum(require_interior=require_interior)

@pytest.mark.parametrize('times',[[0,0],[0],[],[1,0]])
def test_degenerate_interval_rejected(times):
    with pytest.raises(ValueError): line([10,20,30],[1e-3,0,0],knots=times)

def test_quadratic_coordinate_minimum():
    t=np.array([0.,DURATION]); u=t/DURATION
    epochs=Time(EPOCH,u,format='jd',scale='tdb')
    r=np.column_stack([100+(u-.3)**2,np.full(2,10.),np.zeros(2)])
    v=np.column_stack([2*(u-.3)/DURATION,np.zeros((2,2))])
    e=Trajectory(np.column_stack([epochs.jd,r,v]),epochs).minimum()
    assert abs(e['seconds']-.3*DURATION)<1e-6
    assert abs(e['distance_km']-np.sqrt(100**2+10**2))<1e-10

def test_known_distance_and_speed_norms():
    r,v=line([3,4,12],[3/DURATION,4/DURATION,0]).evaluate(0)
    assert np.linalg.norm(r)==13
    assert abs(np.linalg.norm(v)-5/DURATION)<1e-15

def test_zero_distance_range_rate_is_explicitly_undefined():
    e=line([-10,0,0],[20/DURATION,0,0]).minimum()
    assert abs(e['distance_km'])<1e-10
    if e['distance_km']==0:
        assert e['range_rate_kms'] is None

def test_independent_minimizer_failure_is_explicit(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(engine,'minimize_scalar',lambda *a,**k:SimpleNamespace(success=False))
    with pytest.raises(ValueError,match='Independent minimization failed'):
        line([-10,10,0],[20/DURATION,0,0]).minimum()

def test_brent_failure_is_not_silently_ignored(monkeypatch):
    def fail(*a,**k): raise RuntimeError('Deliberate solver failure')
    monkeypatch.setattr(engine,'brentq',fail)
    with pytest.raises(RuntimeError,match='Deliberate solver failure'):
        line([-10,10,0],[20/DURATION,0,0]).minimum()
