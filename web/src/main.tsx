import {useEffect,useMemo,useState} from 'react';
import {createRoot} from 'react-dom/client';
import Scene,{type CameraMode} from './Scene';
import {evaluate,loadBundle,tdbLabel,type Bundle} from './science';
import './style.css';

const tabs=['Encounter','Evidence','Methods','Uncertainty','Sources'] as const;
const number=(x:number,d=1)=>x.toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
function RangeChart({data,t,start,end,onTime}:{data:Bundle;t:number;start:number;end:number;onTime:(t:number)=>void}){
  const values=useMemo(()=>Array.from({length:241},(_,i)=>{const x=start+(end-start)*i/240;return [x,evaluate(data,x).distance];}),[data,start,end]);
  const max=Math.max(...values.map(x=>x[1]))*1.08;
  const x=(time:number)=>20+760*(time-start)/(end-start),y=(range:number)=>115-95*range/max;
  return <div className="range-chart"><div className="chart-heading"><span>GEOCENTRIC RANGE</span><span>{number(max/1000,0)}k km ↕</span></div>
    <svg viewBox="0 0 800 130" role="img" aria-label="Range versus TDB time, with closest-approach and current-time cursors. Use the timeline slider for keyboard control." onPointerDown={e=>{const r=e.currentTarget.getBoundingClientRect();onTime(start+Math.max(0,Math.min(1,((e.clientX-r.left)/r.width*800-20)/760))*(end-start));}}>
      <path d={values.map((v,i)=>`${i?'L':'M'}${x(v[0])},${y(v[1])}`).join(' ')} fill="none" stroke="#68d9e8" strokeWidth="1.5"/>
      <line x1="20" y1="115" x2="780" y2="115" stroke="#26303b"/>
      <line x1={x(data.event_seconds)} x2={x(data.event_seconds)} y1="10" y2="115" stroke="#5b7382" strokeDasharray="3 5"/>
      <line x1={x(t)} x2={x(t)} y1="5" y2="115" stroke="#f4bc79"/>
      <circle cx={x(t)} cy={y(evaluate(data,t).distance)} r="3" fill="#f4bc79"/>
    </svg>
  </div>;
}

function Evidence({data,hash}:{data:Bundle;hash:string}){
  const event=data.results.event,cad=data.results.cad;
  return <><p className="eyebrow">THE EVIDENCE LAB</p><h2>Every curve has a source.</h2><p>This reconstructs JPL information. Horizons and CAD share a model lineage; agreement is not an independent observational confirmation.</p>
    <div className="table-scroll"><table><caption>Reconstruction versus separately acquired JPL CAD · matched solution 220</caption><thead><tr><th>Quantity</th><th>Calculated</th><th>CAD</th><th>Difference</th></tr></thead><tbody>
      <tr><th>Earth-center distance · km</th><td>{number(event.distance_km,6)}</td><td>{number(cad.dist*149597870.7,6)}</td><td>{event.cad_delta_distance_km.toPrecision(5)}</td></tr>
      <tr><th>Epoch · JD TDB</th><td>{event.jd_tdb.toFixed(10)}</td><td>{cad.jd.toFixed(10)}</td><td>{event.cad_delta_seconds.toPrecision(5)} s</td></tr>
      <tr><th>Relative speed · km/s</th><td>{event.speed_kms.toFixed(9)}</td><td>{cad.v_rel.toFixed(9)}</td><td>{event.cad_delta_speed_kms.toExponential(3)}</td></tr>
    </tbody></table></div>
    <h3>Measured convergence</h3><div className="table-scroll"><table><thead><tr><th>Cadence</th><th>Samples</th><th>Minimum km</th><th>CAD time Δ s</th></tr></thead><tbody>{data.results.resolution_study.map(row=><tr key={row.cadence}><th>{row.cadence}</th><td>{row.sample_count}</td><td>{row.distance_km.toFixed(6)}</td><td>{row.cad_delta_seconds.toPrecision(5)}</td></tr>)}</tbody></table></div>
    <p>{data.results.holdout.sample_count} independently queried holdouts: maximum position error {data.results.holdout.max_position_km.toExponential(4)} km; velocity error {data.results.holdout.max_velocity_kms.toExponential(4)} km/s. These measure interpolation error, not physical-orbit accuracy.</p>
    <h3>Frozen provenance</h3><p>Snapshot {data.snapshot_id} · package hash <code>{hash}</code>. Integrity is checked locally before playback. Packaged hashes are not externally authenticated signatures.</p>
    {Object.entries(data.provenance).map(([name,source])=><details key={name}><summary>{name} · API {source.api_signature.version}</summary><p>Retrieved {source.retrieved_utc}</p><p>{source.endpoint}</p><code>{source.sha256}</code><pre>{JSON.stringify(source.parameters,null,2)}</pre></details>)}
  </>;
}

function Mission({data,hash}:{data:Bundle;hash:string}){
  const [t,setT]=useState(data.event_seconds-1200),[playing,setPlaying]=useState(false),[speed,setSpeed]=useState(300),[direction,setDirection]=useState(1);
  const [camera,setCamera]=useState<CameraMode>('Earth'),[visible,setVisible]=useState(true),[quality,setQuality]=useState('Balanced'),[force2d,setForce2d]=useState(false),[vectors,setVectors]=useState(false),[wide,setWide]=useState(false);
  const readTab=()=>{const found=tabs.find(x=>x.toLowerCase()===location.hash.slice(1));return found??'Encounter';};
  const [tab,setTab]=useState<(typeof tabs)[number]>(readTab);
  const start=wide?data.coarse[0][0]:data.fine[0][0],end=wide?data.coarse.at(-1)![0]:data.fine.at(-1)![0];
  const state=useMemo(()=>evaluate(data,t),[data,t]);
  useEffect(()=>{const route=()=>setTab(readTab());addEventListener('hashchange',route);return()=>removeEventListener('hashchange',route);},[]);
  useEffect(()=>{const pause=()=>{if(document.hidden)setPlaying(false);};const blur=()=>setPlaying(false);document.addEventListener('visibilitychange',pause);addEventListener('blur',blur);return()=>{document.removeEventListener('visibilitychange',pause);removeEventListener('blur',blur);};},[]);
  useEffect(()=>{if(!playing)return;let id=0,last=performance.now(),lastDraw=last;
    const tick=(now:number)=>{if(now-lastDraw>=32){const dt=Math.min((now-last)/1000,.2);last=now;lastDraw=now;setT(old=>{const next=old+dt*speed*direction;if(next<=start||next>=end){setPlaying(false);return Math.max(start,Math.min(end,next));}return next;});}id=requestAnimationFrame(tick);};id=requestAnimationFrame(tick);return()=>cancelAnimationFrame(id);
  },[playing,speed,direction,start,end]);
  useEffect(()=>{const key=(e:KeyboardEvent)=>{if((e.target as HTMLElement).closest('input,select,button,a,summary'))return;if(e.code==='Space'){e.preventDefault();setPlaying(p=>!p);}if(e.key.toLowerCase()==='c'){setPlaying(false);setT(data.event_seconds);}};addEventListener('keydown',key);return()=>removeEventListener('keydown',key);},[data]);
  const selectTime=(value:number)=>{setPlaying(false);setT(Math.max(start,Math.min(end,value)));};
  const atMinimum=Math.abs(t-data.event_seconds)<.01;
  return <main data-testid="mission" data-selected-time={t}>
    <p className="sr-only" aria-live="polite">{playing?'Playback running. Pause to hear the selected encounter metrics.':`${tdbLabel(data,t)}. Earth-center distance ${number(state.distance)} kilometers. Relative speed ${number(state.speed,3)} kilometers per second.`}</p>
    <header><a href="#encounter" className="brand"><span className="orbit-icon">◎</span><span>APOPHIS <em>2029</em><small>THE NEAR-MISS ENGINE</small></span></a><div className="header-end"><span className="source-credit">NASA / JPL DATA<br/><small>FROZEN SOLUTION 220</small></span><span className="safe"><i/>Safe flyby · no predicted impact</span></div></header>
    <section className="mission-intro"><div><p className="eyebrow">13 APRIL 2029 / ENCOUNTER RECONSTRUCTION</p><h1>A close encounter.<br/><span>An open record.</span></h1></div><p className="intro-copy">Follow a safe passage past Earth.<br/>Explore the trajectory. Inspect the evidence.</p></section>
    <section className="observatory" aria-label="Encounter explorer">
      <div className="scene-panel"><Scene data={data} t={t} mode={camera} visible={visible} quality={quality} force2d={force2d} vectors={vectors}/>
        <div className="scene-top"><span className="live-status"><i/> {atMinimum?'CLOSEST APPROACH':state.rangeRate<0?'APPROACHING EARTH':'RECEDING FROM EARTH'}</span><span>ICRF · KM-S · TDB</span></div>
        <div className="scene-bottom"><div><strong>EARTH</strong><span>6,371 km reference radius</span></div><div className="asteroid-legend"><i/>APOPHIS · {force2d?'ENLARGED 2D MARKER':visible?'ENLARGED MARKER':'PHYSICAL SIZE'}</div></div>
      </div>
      <aside className="telemetry" aria-label="Selected-time scientific metrics"><p className="eyebrow">ENCOUNTER TELEMETRY</p><div className="datum"><label>EARTH-CENTER DISTANCE</label><strong><output aria-live="off" data-testid="distance" data-value={state.distance}>{number(state.distance)}</output><span>km</span></strong><small>Geocentric · calculated from JPL states</small></div>
        <div className="datum"><label>APPROXIMATE ALTITUDE</label><strong><output aria-live="off" data-testid="altitude" data-value={state.altitude}>{number(state.altitude)}</output><span>km</span></strong><small>Spherical Earth · radius 6,371 km</small></div>
        <div className="datum compact"><label>RELATIVE SPEED</label><strong><output aria-live="off" data-testid="speed" data-value={state.speed}>{number(state.speed,3)}</output><span>km/s</span></strong></div>
        <div className="camera-control"><label htmlFor="camera">CAMERA</label><select id="camera" value={camera} onChange={e=>setCamera(e.target.value as CameraMode)}>{['Earth','Chase','Wide','Scientific'].map(x=><option key={x}>{x}</option>)}</select></div>
        <label className="check"><input type="checkbox" checked={visible} onChange={e=>setVisible(e.target.checked)}/> Enlarge asteroid marker</label>
        <label className="check"><input type="checkbox" checked={vectors} onChange={e=>setVectors(e.target.checked)}/> Velocity direction arrow</label>
        <label className="check"><input type="checkbox" checked={force2d} onChange={e=>setForce2d(e.target.checked)}/> Scientific 2D projection</label>
        <div className="camera-control"><label htmlFor="quality">RENDER QUALITY</label><select id="quality" value={quality} onChange={e=>setQuality(e.target.value)}><option>Balanced</option><option>Low</option></select></div>
        <p className="scale-note">Earth and trajectory share a distance scale. The amber marker is enlarged for visibility; physical body size is approximate. Lighting, stars and globe grid are illustrative. The arrow shows direction only.</p>
      </aside>
    </section>
    <section className="timeline" aria-label="Playback controls"><div className="timeline-heading"><span>SELECTED EPOCH <output aria-live="off" data-testid="epoch">{tdbLabel(data,t)}</output></span><button className="text-button" onClick={()=>{setPlaying(false);setT(data.event_seconds);}}>↗ Closest approach</button></div>
      <input className="scrubber" aria-label="Encounter timeline in elapsed TDB seconds" type="range" min={start} max={end} step="0.1" value={t} onChange={e=>selectTime(Number(e.target.value))}/>
      <div className="playback"><div className="transport"><button aria-label="Rewind to start" onClick={()=>selectTime(start)}>↤</button><button className="play" aria-label={playing?'Pause playback':'Play playback'} onClick={()=>setPlaying(p=>!p)}>{playing?'Ⅱ':'▶'}</button><button aria-pressed={direction<0} onClick={()=>setDirection(d=>-d)}>Reverse {direction<0?'ON':'OFF'}</button><label>Speed <select aria-label="Playback speed" value={speed} onChange={e=>setSpeed(Number(e.target.value))}>{[1,60,300,900,1800].map(x=><option key={x} value={x}>{x}×</option>)}</select></label></div><label className="window-control">Window <select aria-label="Timeline window" value={wide?'wide':'near'} onChange={e=>{const useWide=e.target.value==='wide';setPlaying(false);setWide(useWide);if(!useWide)setT(old=>Math.max(data.fine[0][0],Math.min(data.fine.at(-1)![0],old)));}}><option value="near">Encounter · 4 hours</option><option value="wide">Context · 72 hours</option></select></label></div>
      <RangeChart data={data} t={t} start={start} end={end} onTime={selectTime}/>
    </section>
    <section className="knowledge"><nav aria-label="Scientific information">{tabs.map(x=><a key={x} href={'#'+x.toLowerCase()} aria-current={tab===x?'page':undefined}>{x}</a>)}</nav><article>
      {tab==='Encounter'&&<><p className="eyebrow">THE ENCOUNTER</p><h2>38,011 km from the center of Earth.</h2><p>On April 13, 2029, Apophis makes an exceptionally close, safe passage. This frozen reconstruction places the minimum at approximately <strong>{data.results.time_labels.utc} UTC</strong> ({data.results.time_labels.ist} IST).</p><div className="encounter-facts"><div><span>CALCULATED MINIMUM ALTITUDE</span><strong>{number(data.results.event.approx_altitude_km,0)} km</strong><small>Approximate spherical surface</small></div><div><span>FROZEN JPL SOLUTION</span><strong>220</strong><small>Horizons + CAD + SBDB matched</small></div><div><span>RECONSTRUCTION</span><strong>Validated G0 / M1</strong><small>Browser release validation in progress</small></div></div><p>The asteroid body marker is a visibility aid. Every distance and velocity readout comes from the same geometric state-vector interpolation. No impact prediction is performed here.</p><p className="footnote">Future UTC/IST depends on leap-second assumptions. The timeline is labeled TDB, the authoritative calculation time scale. Space: play/pause when not in a control. C: closest approach.</p></>}
      {tab==='Evidence'&&<Evidence data={data} hash={hash}/>}
      {tab==='Methods'&&<><p className="eyebrow">NUMERICAL METHOD</p><h2>Find the minimum. Preserve the context.</h2><p>Earth-centered geometric positions and velocities are returned by JPL Horizons in ICRF, KM-S, TDB. Fractional TDB calendar epochs are retained using two-part Julian Dates before conversion to elapsed seconds.</p><ol><li>Validate target, center, frame, units, cadence, source hashes and compatible orbit solution.</li><li>Interpolate positions with cubic Hermite polynomials using source velocities as derivatives in seconds.</li><li>Inspect segment stationary roots where r · v = 0; verify a bracketed minimum and compare with bounded scalar minimization.</li><li>Compare with separately frozen JPL CAD; repeat at 300, 60 and 10-second spacing and test all 240 offset observations.</li></ol><p>The browser uses the same Hermite model and freezes the time when paused, scrubbing, hidden or unfocused. The public source archive provides the numerical code; original historical stage reports are held separately and are not bundled.</p><h3>Limits</h3><ul>{data.results.limitations.map(x=><li key={x}>{x}</li>)}</ul></>}
      {tab==='Uncertainty'&&<><p className="eyebrow">FORMAL ENCOUNTER UNCERTAINTY</p><h2>Bounds, with their meaning intact.</h2><p>JPL CAD gives a nominal Earth-center distance of <strong>{number(data.results.cad.dist*149597870.7,3)} km</strong>. Its formal three-sigma distance bounds are <strong>{number(data.results.cad.dist_min*149597870.7,3)}–{number(data.results.cad.dist_max*149597870.7,3)} km</strong>. Formatted time uncertainty: <strong>{data.results.cad.t_sigma_f}</strong> (hours:minutes).</p><p>These are formal encounter quantities for the frozen solution, not a complete trajectory covariance, empirical distribution, or impact probability. We do not sample independent marginal values into invented possible paths.</p><p>NASA describes the flyby as safe, with no predicted Apophis impact risk for at least the next century. This project reproduces JPL information; it does not independently establish that assessment.</p></>}
      {tab==='Sources'&&<><p className="eyebrow">SOURCES & REPRODUCTION</p><h2>Frozen inputs. Open inspection.</h2><p>Snapshot <strong>{data.snapshot_id}</strong> · orbit 220. The user-generated local data bundle exposes source provenance and response hashes. Historical source responses, including unsuccessful acquisition evidence, are kept privately by the maintainer and excluded from the public code package. The browser never calls JPL APIs.</p><ul>{[['NASA Apophis overview','https://science.nasa.gov/solar-system/asteroids/apophis/'],['JPL Horizons documentation','https://ssd.jpl.nasa.gov/horizons/manual.html'],['Horizons API','https://ssd-api.jpl.nasa.gov/doc/horizons.html'],['JPL Close Approach Data API','https://ssd-api.jpl.nasa.gov/doc/cad.html'],['JPL Small-Body Database API','https://ssd-api.jpl.nasa.gov/doc/sbdb.html']].map(([label,url])=><li key={url}><a href={url} target="_blank" rel="noreferrer">{label} ↗</a></li>)}</ul><p>Independent software project. No NASA/JPL sponsorship or endorsement. Source data are attributed to NASA/JPL; all scene geometry is procedural and illustrative.</p><p>To reproduce from public source, follow <code>README.md</code> and <code>TESTING.md</code>. The source-only archive does not include historical snapshots or stage reports. Reacquiring JPL data requires compliance with JPL API policy; redistribution of generated outputs requires a separate rights review.</p></>}
    </article></section>
    <footer><span>APOPHIS 2029 / THE NEAR-MISS ENGINE</span><span>SCIENCE FIRST. EVERY KILOMETER ACCOUNTABLE.</span></footer>
  </main>;
}

function App(){const [loaded,setLoaded]=useState<{data:Bundle;hash:string}|null>(null),[error,setError]=useState('');useEffect(()=>{let active=true;loadBundle().then(value=>{if(active)setLoaded(value);}).catch(e=>{if(active)setError(String(e.message));});return()=>{active=false;};},[]);return error?<main className="loading" role="alert"><h1>Snapshot unavailable</h1><p>{error}</p><p>Serve the complete static build locally, including matching snapshot and manifest files.</p></main>:loaded?<Mission {...loaded}/>:<main className="loading"><p className="eyebrow">APOPHIS 2029</p><h1>Verifying the frozen record.</h1><p>Checking local snapshot integrity before playback…</p></main>;}
createRoot(document.getElementById('root')!).render(<App/>);
