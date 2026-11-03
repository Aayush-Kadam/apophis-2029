import fs from 'node:fs';
import assert from 'node:assert/strict';
import {evaluate,validateBundle,tdbLabel} from '../src/science.ts';
const data=validateBundle(JSON.parse(fs.readFileSync(new URL('../public/snapshots/encounter.json',import.meta.url),'utf8')));
let maxDistance=0,maxSpeed=0;
data.validation_fixtures.seconds.forEach((t,i)=>{
  const state=evaluate(data,t);
  maxDistance=Math.max(maxDistance,Math.abs(state.distance-data.validation_fixtures.expected_distance_km[i]));
  maxSpeed=Math.max(maxSpeed,Math.abs(state.speed-data.validation_fixtures.expected_speed_kms[i]));
});
assert(maxDistance<1e-8); assert(maxSpeed<1e-9);
const event=evaluate(data,data.event_seconds);
assert(Math.abs(event.distance-data.results.event.distance_km)<1e-8);
assert(Math.abs(event.speed-data.results.event.speed_kms)<1e-9);
assert.throws(()=>evaluate(data,-1));
for(const row of data.coarse){
  if(row[0]>=data.fine[0][0]&&row[0]<=data.fine.at(-1)![0])continue;
  const value=evaluate(data,row[0]);
  assert(Math.abs(value.distance-Math.hypot(...row.slice(1,4)))<1e-8);
  assert(Math.abs(value.speed-Math.hypot(...row.slice(4,7)))<1e-9);
}
const invalid=structuredClone(data);invalid.fine[1][0]=invalid.fine[0][0];
assert.throws(()=>validateBundle(invalid));
assert(tdbLabel(data,data.event_seconds).startsWith('2029-04-13 21:46:12'));
console.log(JSON.stringify({holdouts_compared:data.validation_fixtures.seconds.length,max_distance_difference_km:maxDistance,max_speed_difference_kms:maxSpeed,event_distance_km:event.distance,event_speed_kms:event.speed,passed:true},null,2));
