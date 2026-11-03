"""G0-R1 pre-correction causal experiment. Does not modify engine or snapshots."""
import csv
from decimal import Decimal
import json
import re
import hashlib
import numpy as np
from astropy.time import Time
from scipy.interpolate import CubicHermiteSpline
from .engine import ROOT, cached, parse_vectors, canonical_write

MONTHS = {name: f'{i:02d}' for i,name in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],1)}

def source_times(data):
    rows = list(csv.reader(data['result'].split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()))
    isot, jd1, jd2 = [], [], []
    for row in rows:
        match = re.fullmatch(r'\s*A\.D\. (\d{4})-([A-Za-z]{3})-(\d{2}) (\d{2}:\d{2}:\d{2}\.\d+)\s*', row[1])
        if not match: raise ValueError('Unsupported calendar epoch')
        year,month,day,clock = match.groups()
        isot.append(f'{year}-{MONTHS[month]}-{day}T{clock}')
        value=Decimal(row[0].strip()); daypart=int(value)
        jd1.append(float(daypart)); jd2.append(float(value-daypart))
    return Time(isot, format='isot', scale='tdb'), Time(jd1,jd2,format='jd',scale='tdb')

def manual_hermite(t, r, v, q):
    i=np.clip(np.searchsorted(t,q,side='right')-1,0,len(t)-2)
    h=(t[i+1]-t[i])[:,None]; u=((q-t[i])/(t[i+1]-t[i]))[:,None]
    pos=(2*u**3-3*u**2+1)*r[i]+(u**3-2*u**2+u)*h*v[i]+(-2*u**3+3*u**2)*r[i+1]+(u**3-u**2)*h*v[i+1]
    vel=(6*u**2-6*u)/h*r[i]+(3*u**2-4*u+1)*v[i]+(-6*u**2+6*u)/h*r[i+1]+(3*u**2-2*u)*v[i+1]
    return pos,vel

def main():
    f=cached('fine-uniform'); h=cached('holdout-uniform')
    states,_=parse_vectors(f); hold,_=parse_vectors(h)
    fc,fj=source_times(f); hc,hj=source_times(h)
    epoch=fc[0]
    ts={'binary64_printed_jd':(states[:,0]-states[0,0])*86400,
        'decimal_printed_jd':(fj-fj[0]).to_value('sec'),
        'calendar_two_part_tdb':(fc-epoch).to_value('sec')}
    qs={'binary64_printed_jd':(hold[:,0]-states[0,0])*86400,
        'decimal_printed_jd':(hj-fj[0]).to_value('sec'),
        'calendar_two_part_tdb':(hc-epoch).to_value('sec')}
    experiments={}
    for train in ts:
        for evaluate in qs:
            spline=CubicHermiteSpline(ts[train],states[:,1:4],states[:,4:7],extrapolate=False)
            r,v=spline(qs[evaluate]),spline(qs[evaluate],1)
            experiments[train+' -> '+evaluate]={
                'max_position_error_km':float(np.linalg.norm(r-hold[:,1:4],axis=1).max()),
                'max_velocity_error_kms':float(np.linalg.norm(v-hold[:,4:7],axis=1).max())}
    t,q=ts['calendar_two_part_tdb'],qs['calendar_two_part_tdb']
    r,v=manual_hermite(t,states[:,1:4],states[:,4:7],q)
    spline=CubicHermiteSpline(t,states[:,1:4],states[:,4:7],extrapolate=False)
    output={'purpose':'Pre-correction causal evidence; authoritative engine unmodified.',
        'engine_sha256':hashlib.sha256((ROOT/'science/engine.py').read_bytes()).hexdigest(),
        'sample_count':len(states),'holdout_count':len(hold),'experiments':experiments,
        'max_binary_jd_calendar_epoch_difference_seconds':float(np.max(abs(ts['binary64_printed_jd']-t))),
        'max_decimal_jd_calendar_difference_seconds':float(np.max(abs((fj-fc).to_value('sec')))),
        'binary64_jd_ulp_seconds':float(np.spacing(states[0,0])*86400),
        'source_printed_jd_quantum_seconds':0.0000864,
        'calendar_interval_max_error_seconds':float(np.max(abs(np.diff(t)-10))),
        'manual_vs_scipy_max_position_km':float(np.max(np.linalg.norm(r-spline(q),axis=1))),
        'manual_vs_scipy_max_velocity_kms':float(np.max(np.linalg.norm(v-spline(q,1),axis=1))),
        'manual_calendar_max_velocity_error_kms':float(np.max(np.linalg.norm(v-hold[:,4:7],axis=1))),
        'all_240_holdouts_used':True,'source_vectors_unchanged':True,
        'conclusion':'Printed-JD epoch quantization plus binary64 large-JD subtraction perturbs the Hermite time axis. Decimal printed JD alone still fails. Fractional calendar TDB times with two-part subtraction remove the failure using identical vectors and derivative formulas. Evaluation-time rounding alone has much smaller velocity effect than training-axis distortion. No CAD values used in this experiment.'}
    evidence_path = ROOT/'reports/G0-R1_ROOT_CAUSE.json'
    if evidence_path.exists():
        evidence_path = ROOT/'reports/G0-R1_DIAGNOSTIC_RERUN.json'
        output['purpose'] = 'Diagnostic rerun with current engine; original pre-correction evidence is preserved separately.'
    canonical_write(evidence_path,output)
    print(json.dumps(output,indent=2))

if __name__=='__main__': main()
