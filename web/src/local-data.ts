import {validateBundle,type Bundle,evaluate} from './science.ts';
export const HISTORICAL_PAYLOAD_SHA256='52867c459fe206ac73ca1d0a69da39855fe78064e92b417a608372e9ee5cbaa6';
export type ImportResult={data:Bundle;hash:string;verification:'historical-byte-match'|'compatible-unverified'};
const object=(x:unknown):x is Record<string,any>=>!!x&&typeof x==='object'&&!Array.isArray(x);
function requireValue(ok:unknown,message:string):asserts ok{if(!ok)throw Error(message);}
function safeStructure(value:unknown){const stack:[unknown,number][]=[[value,0]];let count=0;while(stack.length){const [v,d]=stack.pop()!;requireValue(++count<100000&&d<=24,'Input is too complex or deeply nested.');if(v&&typeof v==='object'){for(const key of Object.keys(v)){requireValue(!['__proto__','prototype','constructor'].includes(key),'Unsafe JSON key rejected.');stack.push([(v as any)[key],d+1]);}}else if(typeof v==='string')requireValue(v.length<=8192,'Metadata string is too large.');}}
const finite=(x:unknown)=>typeof x==='number'&&Number.isFinite(x);
function validTimestamp(value:unknown,offsetMinutes:number):boolean{
 if(typeof value!=='string')return false;
 const utc=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/;
 const ist=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+05:30$/;
 if(!(offsetMinutes===0?utc:ist).test(value))return false;
 const stamp=Date.parse(value);if(!Number.isFinite(stamp))return false;
 // Date.parse normalizes some impossible dates (e.g. February31). Reject them.
 return new Date(stamp+offsetMinutes*60000).toISOString().slice(0,19)===value.slice(0,19);
} 
const plain=(value:unknown)=>String(value??'').replace(/^'|'$/g,'');
export function validateScientificContract(value:unknown):Bundle{
 requireValue(object(value),'Payload must be a versioned object.');safeStructure(value);
 requireValue(value.schema_version==='1.0','Unsupported payload schema. Expected 1.0.');
 requireValue(value.orbit_id==='220'&&value.time_scale==='TDB'&&value.frame==='Earth-centered ICRF, FRAME, geometric NONE','Incompatible orbit, frame or time scale. Supported: orbit 220, Earth-centered ICRF/FRAME, geometric NONE, TDB.');
 requireValue(object(value.units)&&value.units.position==='km'&&value.units.velocity==='km/s'&&value.units.elapsed_time==='s','Incompatible units. Expected km, km/s and seconds.');
 requireValue(typeof value.snapshot_id==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(value.snapshot_id),'Invalid snapshot identity.');
 requireValue(finite(value.origin_jd_tdb1)&&finite(value.origin_jd_tdb2)&&Math.abs(value.origin_jd_tdb2)<=.5&&Math.abs((value.origin_jd_tdb1-2462238.5)+value.origin_jd_tdb2)<1e-8,'Unsupported reference epoch; expected 2029-Apr-12 00:00 TDB.');
 for(const [name,count,step] of [['coarse',865,300],['fine',1441,10]] as const){
  const rows=value[name];requireValue(Array.isArray(rows)&&rows.length===count,`Missing or truncated ${name} samples; expected ${count}.`);
  rows.forEach((row:any,i:number)=>{requireValue(Array.isArray(row)&&row.length===7&&row.every(finite),`Non-finite or malformed ${name} row.`);requireValue(Math.hypot(...row.slice(1,4))>0&&Math.hypot(...row.slice(1,4))<1e9&&Math.hypot(...row.slice(4,7))<=200,'Implausible KM-S state.');if(i)requireValue(row[0]>rows[i-1][0]&&Math.abs(row[0]-rows[i-1][0]-step)<1e-6,`Unordered or gapped ${name} timestamps.`);});
 }
 requireValue(Math.abs(value.coarse[0][0])<1e-6&&value.fine[0][0]>=value.coarse[0][0]&&value.fine.at(-1)[0]<=value.coarse.at(-1)[0],'Source windows are incompatible.');
 requireValue(Math.abs(value.fine[0][0]-157560)<1e-6,'Fine-window reference timestamp mismatch.');
 requireValue(value.earth_radius_km===6371,'Unsupported Earth radius convention.');
 requireValue(object(value.provenance),'Unverified input: source provenance is missing.');
 const sources:Record<string,[string,string[]]>={
  'coarse-numbered':['https://ssd.jpl.nasa.gov/api/horizons.api',['1.2','1.3']],
  'fine-uniform':['https://ssd.jpl.nasa.gov/api/horizons.api',['1.2','1.3']],
  'holdout-uniform':['https://ssd.jpl.nasa.gov/api/horizons.api',['1.2','1.3']],
  cad:['https://ssd-api.jpl.nasa.gov/cad.api',['1.5']],sbdb:['https://ssd-api.jpl.nasa.gov/sbdb.api',['1.3']]};
 for(const [name,[endpoint,versions]] of Object.entries(sources)){
  const source=value.provenance[name];requireValue(object(source)&&source.endpoint===endpoint&&/^[a-f0-9]{64}$/.test(source.sha256),'Unverified or incompatible source provenance: '+name);
  requireValue(validTimestamp(source.retrieved_utc,0),'Invalid provenance retrieval timestamp.');
  requireValue(object(source.api_signature)&&typeof source.api_signature.source==='string'&&source.api_signature.source.includes('NASA/JPL')&&versions.includes(source.api_signature.version),'Unsupported source signature/version.');
  requireValue(object(source.parameters),'Missing source request contract.');
  if(name.includes('uniform')||name==='coarse-numbered')for(const [k,v] of Object.entries({COMMAND:'99942;',EPHEM_TYPE:'VECTORS',CENTER:'500@399',REF_PLANE:'FRAME',REF_SYSTEM:'ICRF',VEC_CORR:'NONE',OUT_UNITS:'KM-S',VEC_TABLE:'2',TIME_TYPE:'TDB',CSV_FORMAT:'YES'}))requireValue(plain(source.parameters[k])===v,'Incompatible provenance coordinate/time contract.');
  else requireValue(source.parameters.des==='99942','Wrong provenance object.');
  if(name==='coarse-numbered')requireValue(plain(source.parameters.START_TIME)==='2029-Apr-12'&&plain(source.parameters.STOP_TIME)==='2029-Apr-15'&&plain(source.parameters.STEP_SIZE)==='5 m','Incompatible coarse request window.');
  if(name==='fine-uniform')requireValue(plain(source.parameters.START_TIME)==='2029-Apr-13 19:46'&&plain(source.parameters.STOP_TIME)==='2029-Apr-13 23:46'&&plain(source.parameters.STEP_SIZE)==='1440','Incompatible fine request window.');
  if(name==='holdout-uniform')requireValue(plain(source.parameters.START_TIME)==='2029-Apr-13 19:46:07'&&plain(source.parameters.STOP_TIME)==='2029-Apr-13 23:45:07'&&plain(source.parameters.STEP_SIZE)==='239','Incompatible holdout request window.');
  if(name==='cad')requireValue(source.parameters.body==='Earth'&&source.parameters['date-min']==='2029-04-12'&&source.parameters['date-max']==='2029-04-15','Wrong CAD body/date contract.');
 }
 const r=value.results;requireValue(object(r)&&object(r.event)&&object(r.cad)&&object(r.metadata),'Missing scientific results/metadata.');
 requireValue(r.metadata.center==='500@399'&&r.metadata.reference_system==='ICRF'&&r.metadata.reference_plane==='FRAME'&&r.metadata.correction==='NONE'&&r.metadata.time_scale==='TDB'&&r.metadata.units==='KM-S','Inconsistent result coordinate/time metadata.');
 requireValue(r.metadata.orbit_id==='220'&&r.cad.orbit_id==='220'&&r.metadata.target_designation==='99942','Mismatched result/source orbit identity.');
 for(const key of ['jd_tdb','jd_tdb1','jd_tdb2','distance_km','speed_kms','seconds','cad_delta_seconds','cad_delta_distance_km','cad_delta_speed_kms','approx_altitude_km','crosscheck_delta_seconds','range_rate_kms'])requireValue(finite(r.event[key]),'Non-finite event field: '+key);
 for(const key of ['jd','dist','dist_min','dist_max','v_rel'])requireValue(finite(r.cad[key])&&r.cad[key]>0,'Invalid CAD summary.');
 requireValue(r.cad.dist_min<=r.cad.dist&&r.cad.dist<=r.cad.dist_max,'Inverted uncertainty interval.');
 requireValue(object(r.time_labels)&&['utc','ist','caveat'].every(k=>typeof r.time_labels[k]==='string')&&Array.isArray(r.limitations)&&r.limitations.every((v:any)=>typeof v==='string'),'Missing time labels or scientific limitations.');
 requireValue(validTimestamp(r.time_labels.utc,0)&&validTimestamp(r.time_labels.ist,330)&&Math.abs(Date.parse(r.time_labels.utc)-Date.parse(r.time_labels.ist))<=1,'Malformed or inconsistent UTC/IST display timestamps.');
 requireValue(object(r.holdout)&&r.holdout.sample_count===240&&finite(r.holdout.max_position_km)&&finite(r.holdout.max_velocity_kms)&&r.holdout.max_position_km>=0&&r.holdout.max_velocity_kms>=0,'Invalid holdout metadata.');
 requireValue(object(r.checks)&&Object.keys(r.checks).length>=11&&Object.values(r.checks).every(v=>v===true),'Scientific acceptance is not reported as passing. This is not an authenticity guarantee.');
 const data=validateBundle(value as Bundle);const state=evaluate(data,data.event_seconds);
 requireValue(Math.abs(state.distance-r.event.distance_km)<1e-8&&Math.abs(state.speed-r.event.speed_kms)<1e-9,'Event summary is inconsistent with supplied vectors.');
 requireValue(Math.abs(((r.event.jd_tdb1-data.origin_jd_tdb1)+(r.event.jd_tdb2-data.origin_jd_tdb2))*86400-data.event_seconds)<.001,'Event epoch/relative-time mismatch.');
 return data;
}
export async function readLocalScientificFiles(files:readonly File[]):Promise<ImportResult>{
 requireValue(files.length===2,'Select exactly manifest.json and encounter.json.');
 const named=new Map(files.map(f=>[f.name,f]));requireValue(named.size===2&&named.has('manifest.json')&&named.has('encounter.json'),'Select the two expected filenames only.');
 const mf=named.get('manifest.json')!,pf=named.get('encounter.json')!;requireValue(mf.size>0&&mf.size<=16384&&pf.size>0&&pf.size<=4*1024*1024,'Empty input or bounded import size exceeded.');
 const decoder=new TextDecoder('utf-8',{fatal:true});let manifest:any,payload:any;let bytes:ArrayBuffer;
 try{manifest=JSON.parse(decoder.decode(await mf.arrayBuffer()));bytes=await pf.arrayBuffer();payload=JSON.parse(decoder.decode(bytes));}catch{throw Error('Malformed, truncated or non-UTF-8 JSON input.');}
 safeStructure(manifest);requireValue(object(manifest)&&manifest.schema_version==='1.0'&&object(manifest.files)&&Object.keys(manifest.files).join(',')==='encounter.json'&&/^[a-f0-9]{64}$/.test(manifest.files['encounter.json']),'Unsupported local manifest contract.');
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes!)),n=>n.toString(16).padStart(2,'0')).join('');requireValue(hash===manifest.files['encounter.json'],'Local payload checksum mismatch.');
 const data=validateScientificContract(payload);requireValue(data.snapshot_id===manifest.snapshot_id,'Local snapshot identity mismatch.');
 return {data,hash,verification:hash===HISTORICAL_PAYLOAD_SHA256?'historical-byte-match':'compatible-unverified'};
}
