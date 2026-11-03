"""Offline reproducible encounter experiment. Run: python -m science.run"""
import json
import time
import warnings
import numpy as np
import psutil
from astropy.time import Time
from .engine import (ROOT, SNAPSHOT, ANALYSIS, AU_KM, Trajectory, cached, parse_vectors,
                     parse_vector_epochs, parse_cad, canonical_write, time_labels)

def experiment():
    start = time.perf_counter()
    bounds = json.loads((ROOT / 'data/acceptance.json').read_text())
    coarse, metadata = parse_vectors(cached('coarse-numbered'))
    fine, fine_meta = parse_vectors(cached('fine-uniform'))
    holdout, hold_meta = parse_vectors(cached('holdout-uniform'))
    coarse_epochs = parse_vector_epochs(cached('coarse-numbered'))
    fine_epochs = parse_vector_epochs(cached('fine-uniform'))
    holdout_epochs = parse_vector_epochs(cached('holdout-uniform'))
    cad = parse_cad(cached('cad'))
    sbdb = cached('sbdb')
    if not metadata['orbit_id'] == fine_meta['orbit_id'] == hold_meta['orbit_id'] == cad['orbit_id'] == sbdb['orbit']['orbit_id']:
        raise ValueError('Orbit solution mismatch: comparison LIMITED')
    results = []
    cad_epoch = Time(cad['jd_tdb1'], cad['jd_tdb2'], format='jd', scale='tdb')
    for name, states, epochs in [('300s', coarse, coarse_epochs), ('60s', fine[::6], fine_epochs[::6]), ('10s', fine, fine_epochs)]:
        traj = Trajectory(states, epochs)
        event = traj.minimum()
        event.update({'cad_delta_seconds': float((Time(event['jd_tdb1'], event['jd_tdb2'], format='jd',scale='tdb')-cad_epoch).to_value('sec')),
                      'cad_delta_distance_km': event['distance_km']-cad['dist']*AU_KM,
                      'cad_delta_speed_kms': event['speed_kms']-cad['v_rel'],
                      'cadence': name, 'sample_count': len(states)})
        results.append(event)
    traj = Trajectory(fine, fine_epochs)
    q = (holdout_epochs-traj.epoch_tdb).to_value('sec')
    if np.any(np.min(abs(q[:,None]-traj.t), axis=1) < 1):
        raise ValueError('Holdout overlaps training knots')
    predicted_r, predicted_v = traj.evaluate(q)
    pos_error = np.linalg.norm(predicted_r-holdout[:, 1:4], axis=1)
    vel_error = np.linalg.norm(predicted_v-holdout[:, 4:7], axis=1)
    hold = {'sample_count': len(holdout), 'max_position_km': float(pos_error.max()),
            'rms_position_km': float(np.sqrt(np.mean(pos_error**2))),
            'max_velocity_kms': float(vel_error.max()), 'independent_request': True}
    event = results[-1]
    checks = {
        'g0_cad_distance': abs(event['cad_delta_distance_km']) <= bounds['g0_distance_km'],
        'g0_cad_time': abs(event['cad_delta_seconds']) <= bounds['g0_time_seconds'],
        'refined_cad_distance': abs(event['cad_delta_distance_km']) <= bounds['m1_distance_km'],
        'refined_cad_time': abs(event['cad_delta_seconds']) <= bounds['m1_time_seconds'],
        'cad_speed': abs(event['cad_delta_speed_kms']) <= bounds['speed_kms'],
        'holdout_position': hold['max_position_km'] <= bounds['holdout_position_km'],
        'holdout_velocity': hold['max_velocity_kms'] <= bounds['holdout_velocity_kms'],
        'convergence_distance': max(abs(r['distance_km']-event['distance_km']) for r in results) <= bounds['coarse_to_fine_distance_km'],
        'convergence_time': bool(max(abs((Time(r['jd_tdb1'],r['jd_tdb2'],format='jd',scale='tdb')-Time(event['jd_tdb1'],event['jd_tdb2'],format='jd',scale='tdb')).to_value('sec')) for r in results) <= bounds['coarse_to_fine_time_seconds']),
        'independent_minimizer': all(abs(r['crosscheck_delta_seconds']) <= bounds['independent_method_time_seconds'] for r in results),
        'stationarity': abs(event['range_rate_kms']) < 1e-8,
    }
    with warnings.catch_warnings(record=True) as caught:
        labels = time_labels(Time(event['jd_tdb1'],event['jd_tdb2'],format='jd',scale='tdb'))
    output = {'schema_version': '1.2', 'snapshot_id': SNAPSHOT.name, 'software_version': '0.1.2',
        'time_representation': 'Source fractional calendar TDB; Astropy two-part JD subtraction before elapsed seconds; rounded jd_tdb retained only for display/traceability.',
        'algorithm': 'Cubic Hermite position/velocity in seconds; all segment stationary roots inspected; Brent root; bounded scalar crosscheck',
        'metadata': metadata, 'orbit_compatibility': 'MATCHED JPL#220 (common JPL lineage)',
        'cad': cad, 'event': event, 'time_labels': labels,
        'time_conversion_warnings': [str(w.message) for w in caught],
        'resolution_study': results, 'holdout': hold, 'checks': checks,
        'limitations': ['Interpolation of JPL vectors, not independent orbit determination.',
          'Horizons and CAD share JPL model lineage.', 'Spherical altitude uses radius 6371 km.',
          'No Earth geographic orientation or impact/deflection forecasting.',
          'Formal 3-sigma CAD bounds are not full trajectory covariance.', labels['caveat']]}
    out_hash = canonical_write(ANALYSIS/'derived/results.json', output)
    for name, states, epochs in [('coarse', coarse, coarse_epochs), ('fine', fine, fine_epochs), ('holdout', holdout, holdout_epochs)]:
        canonical_write(ANALYSIS/f'normalized/{name}.json', {'metadata': metadata, 'columns': ['jd_tdb_rounded','x_km','y_km','z_km','vx_kms','vy_kms','vz_kms'], 'states': states.tolist(),
            'jd_tdb1': epochs.jd1.tolist(), 'jd_tdb2': epochs.jd2.tolist(), 'elapsed_seconds': (epochs-epochs[0]).to_value('sec').tolist()})
    proc = psutil.Process()
    mem = proc.memory_info()
    bench = {'wall_seconds': time.perf_counter()-start, 'cpu_seconds': sum(proc.cpu_times()[:2]),
             'peak_working_set_bytes': getattr(mem, 'peak_wset', mem.rss),
             'results_sha256': out_hash, 'input_bytes': sum(p.stat().st_size for p in (SNAPSHOT/'raw').glob('*.json'))}
    canonical_write(ROOT/'benchmarks/g0-r2.json', bench)
    print(json.dumps({'event': event, 'holdout': hold, 'checks': checks, 'benchmark': bench}, indent=2))
    return output

if __name__ == '__main__':
    result = experiment()
    if not all(result['checks'].values()):
        raise SystemExit(2)
