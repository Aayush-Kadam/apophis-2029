export type Row = number[];
export interface EventResult { jd_tdb:number; jd_tdb1:number; jd_tdb2:number; distance_km:number; speed_kms:number; seconds:number; cad_delta_seconds:number; cad_delta_distance_km:number; cad_delta_speed_kms:number; approx_altitude_km:number; crosscheck_delta_seconds:number; range_rate_kms:number }
export interface Bundle {
  schema_version:string; snapshot_id:string; orbit_id:string; time_scale:string; frame:string;
  origin_jd_tdb1:number; origin_jd_tdb2:number; earth_radius_km:number;
  units:{position:string;velocity:string;elapsed_time:string}; coarse:Row[]; fine:Row[]; event_seconds:number;
  results:{event:EventResult; cad:{jd:number;dist:number;dist_min:number;dist_max:number;v_rel:number;t_sigma_f:string;orbit_id:string};
    resolution_study:(EventResult & {cadence:string;sample_count:number})[];
    holdout:{sample_count:number;max_position_km:number;max_velocity_kms:number};
    time_labels:{utc:string;ist:string;caveat:string}; limitations:string[]};
  provenance:Record<string,{endpoint:string;parameters:Record<string,string>;retrieved_utc:string;sha256:string;api_signature:{source:string;version:string}}>;
  validation_fixtures:{seconds:number[];expected_distance_km:number[];expected_speed_kms:number[]};
}
export interface State {r:number[];v:number[];distance:number;speed:number;altitude:number;rangeRate:number}

export function validateBundle(value:Bundle):Bundle {
  if(value.schema_version!=='1.0'||value.time_scale!=='TDB'||value.orbit_id!=='220'||value.units.position!=='km'||value.units.velocity!=='km/s'||!value.frame.includes('ICRF')) throw Error('Unsupported scientific data contract');
  for(const rows of [value.coarse,value.fine]) {
    if(!Array.isArray(rows)||rows.length<2) throw Error('Missing frozen vectors');
    rows.forEach((row,i)=>{if(row.length!==7||!row.every(Number.isFinite)||(i>0&&row[0]<=rows[i-1][0])) throw Error('Invalid or unordered state vectors');});
  }
  if(!Number.isFinite(value.event_seconds)||value.event_seconds<value.fine[0][0]||value.event_seconds>value.fine.at(-1)![0]) throw Error('Encounter outside source window');
  return value;
}

export function evaluate(data:Bundle,t:number):State {
  if(!Number.isFinite(t)||t<data.coarse[0][0]||t>data.coarse.at(-1)![0]) throw Error('Time outside frozen ephemeris');
  const rows=t>=data.fine[0][0]&&t<=data.fine.at(-1)![0]?data.fine:data.coarse;
  let lo=0,hi=rows.length-1;
  while(hi-lo>1){const mid=(lo+hi)>>1;if(rows[mid][0]<=t)lo=mid;else hi=mid;}
  const a=rows[lo],b=rows[hi],h=b[0]-a[0],u=(t-a[0])/h;
  const r:number[]=[],v:number[]=[];
  for(let k=0;k<3;k++){
    r.push((2*u**3-3*u*u+1)*a[k+1]+(u**3-2*u*u+u)*h*a[k+4]+(-2*u**3+3*u*u)*b[k+1]+(u**3-u*u)*h*b[k+4]);
    v.push((6*u*u-6*u)/h*a[k+1]+(3*u*u-4*u+1)*a[k+4]+(-6*u*u+6*u)/h*b[k+1]+(3*u*u-2*u)*b[k+4]);
  }
  const distance=Math.hypot(...r),speed=Math.hypot(...v);
  return {r,v,distance,speed,altitude:distance-data.earth_radius_km,rangeRate:r.reduce((sum,x,k)=>sum+x*v[k],0)/distance};
}

export function tdbLabel(data:Bundle,t:number):string {
  // Calendar formatting of TDB itself, deliberately NOT a conversion to UTC.
  const ms=((data.origin_jd_tdb1-2440587.5)+data.origin_jd_tdb2)*86400000+t*1000;
  return new Date(ms).toISOString().replace('T',' ').slice(0,19)+' TDB';
}

export async function loadBundle():Promise<{data:Bundle;hash:string}> {
  const root=import.meta.env.BASE_URL+'snapshots/';
  const response=await fetch(root+'manifest.json'); if(!response.ok) throw Error('Frozen manifest unavailable');
  const manifest=await response.json(); if(manifest.schema_version!=='1.0') throw Error('Unrecognized manifest');
  const payload=await fetch(root+'encounter.json'); if(!payload.ok) throw Error('Frozen snapshot unavailable');
  const bytes=await payload.arrayBuffer();
  const digest=await crypto.subtle.digest('SHA-256',bytes);
  const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
  if(hash!==manifest.files['encounter.json']) throw Error('Snapshot integrity check failed. Please restore the matching frozen files.');
  return {data:validateBundle(JSON.parse(new TextDecoder().decode(bytes))),hash};
}
