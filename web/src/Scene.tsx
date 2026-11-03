import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {evaluate,type Bundle} from './science';

export type CameraMode='Earth'|'Chase'|'Wide'|'Scientific';
type Props={data:Bundle;t:number;mode:CameraMode;visible:boolean;quality:string;force2d:boolean;vectors:boolean};
type Controller={update:(p:Props)=>void;lose:()=>void;restore:()=>void;sample:()=>void};

export function Plot2D({data,t}:{data:Bundle;t:number}){
  const points=data.fine.map(row=>`${250+row[1]/450},${180-row[2]/450}`).join(' ');
  const s=evaluate(data,t);
  return <svg viewBox="0 0 500 360" className="fallback-plot" role="img" aria-label="Earth-centered ICRF X Y projection of the same frozen trajectory; out-of-plane Z omitted">
    <defs><radialGradient id="earth2"><stop stopColor="#245673"/><stop offset="1" stopColor="#0c2030"/></radialGradient></defs>
    <line x1="0" y1="180" x2="500" y2="180" stroke="#203140"/><line x1="250" y1="0" x2="250" y2="360" stroke="#203140"/>
    <circle cx="250" cy="180" r={6371/450} fill="url(#earth2)" stroke="#67b9d6"/>
    <polyline points={points} stroke="#6ce4ef" strokeWidth="1" fill="none"/>
    <circle cx={250+s.r[0]/450} cy={180-s.r[1]/450} r="4" fill="#f7bd78"/>
    <text x="16" y="26" fill="#b4cad8" fontSize="11">ICRF X–Y projection · Z omitted · enlarged marker</text>
  </svg>;
}

export default function Scene(props:Props){
  const host=useRef<HTMLDivElement>(null); const controller=useRef<Controller|null>(null);
  const [failure,setFailure]=useState(false);
  const qa=new URLSearchParams(location.search).has('qa');
  const [stats,setStats]=useState<{draws:number;seconds:number;drawsPerSecond:number;geometries:number;textures:number;heapBytes:number|null}|null>(null);
  useEffect(()=>{
    const container=host.current!; let renderer:THREE.WebGLRenderer;
    try {renderer=new THREE.WebGLRenderer({antialias:false,alpha:true,powerPreference:'low-power'});}
    catch {setFailure(true);return;}
    setFailure(false); renderer.setPixelRatio(Math.min(devicePixelRatio,props.quality==='Low'?1:1.25));
    container.appendChild(renderer.domElement); renderer.domElement.setAttribute('aria-label','Interactive Earth-centered Apophis trajectory');
    const scene=new THREE.Scene(); const camera=new THREE.PerspectiveCamera(39,1,.01,1500);
    const controls=new OrbitControls(camera,renderer.domElement); controls.enableDamping=false; controls.minDistance=1.5;controls.maxDistance=300;
    const light=new THREE.DirectionalLight('#b5e5ff',3);light.position.set(-4,3,7);scene.add(light,new THREE.AmbientLight('#355774',.9));
    const planet=new THREE.Mesh(new THREE.SphereGeometry(1,64,40),new THREE.MeshPhongMaterial({color:'#102c40',emissive:'#020a11',shininess:18}));scene.add(planet);
    const grid=new THREE.Mesh(new THREE.SphereGeometry(1.002,24,14),new THREE.MeshBasicMaterial({color:'#5c9aad',wireframe:true,transparent:true,opacity:.09}));scene.add(grid);
    const atmosphere=new THREE.Mesh(new THREE.SphereGeometry(1.045,48,32),new THREE.ShaderMaterial({transparent:true,side:THREE.BackSide,depthWrite:false,
      vertexShader:'varying vec3 n; varying vec3 eye; void main(){vec4 p=modelViewMatrix*vec4(position,1.0); n=normalize(normalMatrix*normal); eye=normalize(-p.xyz);gl_Position=projectionMatrix*p;}',
      fragmentShader:'varying vec3 n;varying vec3 eye;void main(){float f=pow(1.0-abs(dot(normalize(n),normalize(eye))),3.0);gl_FragColor=vec4(0.26,0.65,0.9,f*0.45);}'}));scene.add(atmosphere);
    const km=1/props.data.earth_radius_km;
    const path=(rows:number[][],color:string,opacity:number)=>{
      const points=rows.map(row=>new THREE.Vector3(row[1]*km,row[2]*km,row[3]*km));
      const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color,transparent:true,opacity}));scene.add(line);
    };
    path(props.data.coarse,'#607a8b',.22);path(props.data.fine,'#68d9e8',.85);
    const mark=new THREE.Mesh(new THREE.IcosahedronGeometry(.07,1),new THREE.MeshStandardMaterial({color:'#f9c57e',emissive:'#ad6020',emissiveIntensity:.7,roughness:.7}));scene.add(mark);
    const halo=new THREE.Mesh(new THREE.SphereGeometry(.13,16,12),new THREE.MeshBasicMaterial({color:'#ffc88b',transparent:true,opacity:.1,depthWrite:false}));scene.add(halo);
    const velocity=new THREE.ArrowHelper(new THREE.Vector3(1,0,0),new THREE.Vector3(),1.2,'#efc18a',.15,.06);scene.add(velocity);
    const axes=new THREE.AxesHelper(2.7);scene.add(axes);
    // Deterministic sparse star decoration; no astronomical catalogue claim.
    const stars:number[]=[]; let seed=99942; const rand=()=>{seed=(seed*16807)%2147483647;return seed/2147483647;};
    for(let i=0;i<450;i++){const z=rand()*2-1,angle=rand()*Math.PI*2,r=Math.sqrt(1-z*z)*170;stars.push(r*Math.cos(angle),r*Math.sin(angle),z*170);}
    const starGeo=new THREE.BufferGeometry();starGeo.setAttribute('position',new THREE.Float32BufferAttribute(stars,3));
    scene.add(new THREE.Points(starGeo,new THREE.PointsMaterial({color:'#a4bfd0',size:.12,transparent:true,opacity:.45})));
    let lastMode='',updating=false,sampling=false,draws=0,sampleStart=0,lastSample=0;
    const position=new THREE.Vector3(),direction=new THREE.Vector3();
    const lossExtension=renderer.getContext().getExtension('WEBGL_lose_context');
    const draw=()=>{
      renderer.render(scene,camera);
      if(qa&&sampling){draws++;const now=performance.now();if(now-lastSample>500){const seconds=(now-sampleStart)/1000;lastSample=now;
        const memory=(performance as Performance & {memory?:{usedJSHeapSize:number}}).memory;
        setStats({draws,seconds,drawsPerSecond:draws/seconds,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,heapBytes:memory?.usedJSHeapSize??null});}}
    };
    const orbitDraw=()=>{if(!updating)draw();};
    const resize=()=>{const width=container.clientWidth,height=container.clientHeight;renderer.setSize(width,height);camera.aspect=width/Math.max(1,height);camera.updateProjectionMatrix();draw();};
    const observer=new ResizeObserver(resize);observer.observe(container);controls.addEventListener('change',orbitDraw);
    const lost=(event:Event)=>{event.preventDefault();setFailure(true);};
    const restored=()=>{setFailure(false);draw();};
    renderer.domElement.addEventListener('webglcontextlost',lost);renderer.domElement.addEventListener('webglcontextrestored',restored);
    controller.current={lose:()=>lossExtension?.loseContext(),restore:()=>lossExtension?.restoreContext(),
      sample:()=>{draws=0;sampleStart=performance.now();lastSample=sampleStart;sampling=true;},update:p=>{
      const state=evaluate(p.data,p.t);position.set(...state.r as [number,number,number]).multiplyScalar(km);
      mark.position.copy(position);halo.position.copy(position);halo.visible=p.visible;
      mark.scale.setScalar(p.visible?1:(.17*km/.07));
      direction.set(...state.v as [number,number,number]).normalize();velocity.position.copy(position);velocity.setDirection(direction);velocity.visible=p.vectors;
      axes.visible=p.mode==='Scientific'; controls.enabled=p.mode!=='Chase';
      if(p.mode!==lastMode){
        if(p.mode==='Earth')camera.position.set(5,3,12);
        if(p.mode==='Wide')camera.position.set(14,12,27);
        if(p.mode==='Scientific')camera.position.set(0,0,28);
        controls.target.set(0,0,0);
        if(p.mode==='Earth'){
          // Frame Earth and the actual encounter together; no geometry scaling.
          const encounter=evaluate(p.data,p.data.event_seconds).r;
          controls.target.set(...encounter as [number,number,number]).multiplyScalar(km*.45);
          camera.position.add(controls.target);
        }
        lastMode=p.mode;
      }
      if(p.mode==='Chase'){camera.position.copy(position).add(new THREE.Vector3(2.5,1.8,4));controls.target.copy(position).multiplyScalar(.6);}
      updating=true;controls.update();updating=false;draw();
    }};
    controller.current.update(props);resize();
    return()=>{controller.current=null;observer.disconnect();controls.dispose();renderer.domElement.removeEventListener('webglcontextlost',lost);renderer.domElement.removeEventListener('webglcontextrestored',restored);
      scene.traverse(object=>{const mesh=object as THREE.Mesh;if(mesh.geometry)mesh.geometry.dispose();if(mesh.material){const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];materials.forEach(material=>material.dispose());}});
      renderer.dispose();renderer.domElement.remove();};
  },[props.data,props.quality]);
  useEffect(()=>{controller.current?.update(props);},[props.t,props.mode,props.visible,props.vectors,props.data,props.quality]);
  return <div className="scene-wrap" data-testid="scene" data-time={props.t}>
    <div className="webgl-host" ref={host} style={{visibility:failure||props.force2d?'hidden':'visible'}}/>
    {(failure||props.force2d)&&<div className="fallback"><Plot2D data={props.data} t={props.t}/><p>{failure?'3D is unavailable. The same frozen trajectory remains available in 2D.':'Scientific 2D projection · same timeline and physical metrics'}</p></div>}
    {qa&&<details className="qa-tools"><summary>Local QA controls</summary><button onClick={()=>controller.current?.lose()}>Simulate WebGL context loss</button><button onClick={()=>controller.current?.restore()}>Restore WebGL context</button><button onClick={()=>controller.current?.sample()}>Begin rendering sample</button><output data-testid="render-statistics">{JSON.stringify(stats)}</output></details>}
    <div className="scene-caption"><span className="tiny-cross">+</span> EARTH-CENTERED ICRF <span>Illustrative globe & lighting · no geographic alignment</span></div>
  </div>;
}
