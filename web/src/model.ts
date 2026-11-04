import {evaluate as interpolate,type Bundle,type State} from './science.ts';
export type RenderData=Pick<Bundle,'coarse'|'fine'|'event_seconds'|'earth_radius_km'>;
// The original scientific interpolation function is unchanged. It reads only
// these rendering fields; no synthetic provenance or historical result is added.
export function evaluate(data:RenderData,t:number):State{return interpolate(data as Bundle,t);}
export function educationalTrajectory():RenderData{
 const rows=Array.from({length:61},(_,i)=>{const t=-5400+i*180;return [t,12*t,24000+.0001*t*t,6000,12,.0002*t,0];});
 return {coarse:rows,fine:rows,event_seconds:0,earth_radius_km:6371};
}
export const EDUCATIONAL_NOTICE='EDUCATIONAL DEMONSTRATION — NOT VERIFIED APOPHIS EPHEMERIDES';
