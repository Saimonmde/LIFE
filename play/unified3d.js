/* SPDX-License-Identifier: AGPL-3.0-or-later */
import * as T from './three.module.js';
import {buildMine} from './mine3d.js?v=saimon-door-r3';
import {enrichWorld} from './park3d.js?v=saimon-door-r3';
import {buildHouse, buildHomeMarker} from './casa3d.js?v=saimon-door-r3';
// The existing game remains the sole owner of simulation, actions, chat and saves.
const BUILD='saimoncity-camera360-r1';
const status=window.LIVE3D={active:false,build:BUILD};
const wait=setInterval(()=>{if(window.LiveInk?.world?.clientReady){clearInterval(wait);try{boot(window.LiveInk);}catch(e){console.error(e);status.error=String(e);document.querySelector('#zona-nombre').textContent='No se pudo iniciar 3D · recarga o activa WebGL';}}},100);
function boot(api){
 const W=api.world,S=api.state;const initialZone=W.mapId==='mine'||W.mapId==='casa'?W.mapId:null;const savedZone=initialZone?Object.fromEntries(Object.keys(W.cityDefinition).map(k=>[k,W[k]])):null;if(initialZone){Object.assign(W,W.cityDefinition);W.mapId='city';}
 const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(innerWidth,innerHeight);renderer.domElement.id='mundo3d';renderer.domElement.style.cssText='position:fixed;inset:0;width:100%;height:100%;touch-action:none;z-index:0';
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;document.body.insertBefore(renderer.domElement,document.body.firstChild); const cv=renderer.domElement;
 const scene=new T.Scene();scene.background=new T.Color('#a4c4bc');scene.fog=new T.Fog('#a4c4bc',110,320);
 const ambient=new T.HemisphereLight(0xffefd3,0x405336,2);scene.add(ambient);const sun=new T.DirectionalLight(0xffedce,2.2);sun.position.set(-30,70,20);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-42,right:42,top:42,bottom:-42,near:1,far:180});sun.shadow.bias=-.001;sun.shadow.normalBias=.04;scene.add(sun);scene.add(sun.target);
 const camera=new T.PerspectiveCamera(45,innerWidth/innerHeight,.1,600);
 const PITCH_MIN=10*Math.PI/180,PITCH_MAX=Math.PI/2;
 const clampYaw=v=>((v%(Math.PI*2))+Math.PI*2)%(Math.PI*2);
 let yaw=.45,pitch=1.12,distance=32;
 // Convert screen-relative input to the nearest walkable grid heading.
 api.keyboardDirection=(dx,dy)=>{
  if(stickX||stickY){dx=stickX;dy=stickY;}
  if(!status.active||(!dx&&!dy))return [dx,dy];
  const x=Math.cos(yaw)*dx+Math.sin(yaw)*dy;
  const y=-Math.sin(yaw)*dx+Math.cos(yaw)*dy;
  const heading=Math.round(Math.atan2(y,x)/(Math.PI/4))*Math.PI/4;
  return [Math.round(Math.cos(heading)),Math.round(Math.sin(heading))];
 };

 // Capture camera shortcuts before the movement handler; never intercept typing.
 let stickX=0,stickY=0;
 const turning=new Set(),zoomKeys=new Set();let zoomHeld=false;let lastFrame=performance.now();
 const editing=()=>document.activeElement?.matches('input,textarea,[contenteditable="true"]');
 addEventListener('keydown',e=>{if(!status.active||editing())return;if(e.key.toLowerCase()==='z'){zoomHeld=true;e.preventDefault();e.stopImmediatePropagation();return;}if(e.shiftKey&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();S.keys.delete(e.key.toLowerCase());turning.add(e.key);}else if(zoomHeld&&['ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();S.keys.delete('arrowup');S.keys.delete('arrowdown');zoomKeys.add(e.key);}else if(['+','=','-'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();distance=Math.max(10,Math.min(110,distance+(e.key==='-'?3:-3)));}},true);
 addEventListener('keyup',e=>{turning.delete(e.key);zoomKeys.delete(e.key);if(e.key.toLowerCase()==='z'){zoomHeld=false;zoomKeys.clear();}if(e.key==='Shift')turning.clear();},true);
 addEventListener('blur',()=>{turning.clear();zoomHeld=false;zoomKeys.clear();});
 function updateZoom(dt){
  const direction=zoomHeld?Number(zoomKeys.has('ArrowDown'))-Number(zoomKeys.has('ArrowUp')):0;
  distance=Math.max(10,Math.min(110,distance*Math.exp(direction*.8*dt)));
 }
 const target=new T.Vector3();const ray=new T.Raycaster(),pointer=new T.Vector2(),pick=[];
 const height=(x,y)=>{
  if(W.mapId==='mine'||W.mapId==='casa')return 0;
  const px=Math.max(0,Math.min(W.width-.001,x+.5)),py=Math.max(0,Math.min(W.height-.001,y+.5)),ix=Math.floor(px),iy=Math.floor(py),u=px-ix,v=py-iy;
  const a=corner(ix,iy),b=corner(ix+1,iy),c=corner(ix,iy+1),d=corner(ix+1,iy+1);
  return v>u?a*(1-v)+c*(v-u)+d*u:a*(1-u)+d*v+b*(u-v);
 };
 const mat=c=>new T.MeshLambertMaterial({color:c,flatShading:true});const cache=new Map();
 function material(c){if(!cache.has(c))cache.set(c,mat(c));return cache.get(c);}
 const geometries=new Map();function geometry(key,build){if(!geometries.has(key))geometries.set(key,build());return geometries.get(key);}
 function box(x,y,z,w,h,d,c){const m=new T.Mesh(geometry(`box:${w},${h},${d}`,()=>new T.BoxGeometry(w,h,d)),material(c));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;scene.add(m);return m;}
 const palette={grass:'#74875b',grass_flowers:'#74875b',grass_worn:'#74875b',path:'#c4ac87',cobble:'#bd886d',pavement:'#aab0b1',creek:'#689598',bridge:'#967247',water:'#357f8b',cliff:'#777769',shore:'#baa47a',mountain:'#718164',rocky:'#929080',asphalt:'#444a4c'};
 // Procedural mountain grain: green slopes, exposed stone and fine contour veins.
 for(const [kind,color] of [['mountain','#718164'],['rocky','#929080'],['asphalt','#444a4c']]){
  const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const c=canvas.getContext('2d');c.fillStyle=color;c.fillRect(0,0,128,128);
  for(let y=0;y<128;y+=2)for(let x=0;x<128;x+=2){const v=((x*73+y*151+x*y*7)%37)-18;c.fillStyle=`rgba(${v>0?'220,224,184':'26,40,31'},${Math.abs(v)/(kind==='asphalt'?160:65)})`;c.fillRect(x,y,2,2);}
  if(kind!=='asphalt'){c.strokeStyle='#b5b09840';c.lineWidth=1;for(let row=0;row<128;row+=19){c.beginPath();for(let x=0;x<=128;x+=4)c.lineTo(x,row+Math.sin(x*.09+row)*7);c.stroke();}}
  const tex=new T.CanvasTexture(canvas);tex.colorSpace=T.SRGBColorSpace;tex.wrapS=tex.wrapT=T.RepeatWrapping;tex.anisotropy=4;const m=material(palette[kind]);m.color.set('#ffffff');m.map=tex;m.needsUpdate=true;
 }
 const groups={};for(let y=0;y<W.height;y++)for(let x=0;x<W.width;x++){let k=W.tiles[W.ground[y][x]].kind;const surface=(W.surfaceZones||[]).find(s=>x>=s.x&&x<s.x+s.w&&y>=s.y&&y<s.y+s.h);if(surface)k=surface.kind;if(k==='water'&&(W.riverLayouts||[]).some(r=>r.axis==='y'&&x>=r.x&&x<r.x+r.w)&&!(W.riverLayouts||[]).some(r=>r.axis==='x'&&y>=r.y&&y<r.y+r.h))k='creek';(groups[k]??=[]).push([x,y]);}
 // Shared corner heights form a continuous surface with no tile-box seams.
 function corner(x,y){let sum=0,n=0;for(const dx of [-1,0])for(const dy of [-1,0]){if(x+dx>=0&&x+dx<W.width&&y+dy>=0&&y+dy<W.height){sum+=W.elevation[y+dy][x+dx];n++;}}return n?sum/n:0;}
 for(const [k,cells] of Object.entries(groups)){const positions=[],uv=[];for(const [x,y] of cells){const v=[[x*2,corner(x,y),y*2],[x*2,corner(x,y+1),(y+1)*2],[(x+1)*2,corner(x+1,y+1),(y+1)*2],[(x+1)*2,corner(x+1,y),y*2]];for(const i of [0,1,2,0,2,3]){positions.push(...v[i]);uv.push(v[i][0]/4,v[i][2]/4);}}const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(positions,3));geo.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geo.computeVertexNormals();const mesh=new T.Mesh(geo,material(palette[k]||'#7b9253'));mesh.receiveShadow=true;scene.add(mesh);mesh.userData.terrain=true;pick.push(mesh);}
 // Low polygon mountains frame the compact, deliberately non-geographic map.
 for(let i=0;i<Math.ceil(W.width*2/9)+6;i++){const x=i*9-25;for(const z of [-17,W.height*2+20]){const m=new T.Mesh(new T.ConeGeometry(13+(i%3)*3,18+(i%5)*5,5),material(i%2?'#62765a':'#738264'));m.position.set(x,8,z);scene.add(m);}}
 // All world props are meshes. Inventory portraits/icons remain ordinary UI images.
 function part(g,shape,pos,scale,c){const mesh=new T.Mesh(shape,material(c));mesh.position.set(...pos);mesh.scale.set(...scale);mesh.castShadow=true;mesh.receiveShadow=true;g.add(mesh);return mesh;}
 const unit=geometry('unit',()=>new T.BoxGeometry(1,1,1)),orb=geometry('orb',()=>new T.IcosahedronGeometry(1,1)),cone=geometry('cone',()=>new T.ConeGeometry(1,1,10)),cylinder=geometry('cylinder',()=>new T.CylinderGeometry(1,1,1,12));
 // Boca de la mina de Las Palmas: marco de madera iluminado, letrero y faro visible de lejos (arte original por código).
 function minePortalSign(text,w,h,font,bg){const c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d');x.fillStyle=bg;x.fillRect(0,0,w,h);x.strokeStyle='#e2b23c';x.lineWidth=Math.max(4,h/12);x.strokeRect(x.lineWidth/2,x.lineWidth/2,w-x.lineWidth,h-x.lineWidth);x.font=font;x.textAlign='center';x.textBaseline='middle';x.fillStyle='#ffe3a0';x.fillText(text,w/2,h/2+2);const t=new T.CanvasTexture(c);t.colorSpace=T.SRGBColorSpace;return t;}
 function buildMinePortal(g,P){
  for(const [x,y,z,sx,sy,sz,c] of [[0,2.3,-1.5,3.6,2.8,1.9,'#6d675b'],[-2.3,1.3,-.8,1.5,1.6,1.4,'#5d584d'],[2.3,1.4,-.9,1.6,1.8,1.4,'#76705f']])P(orb,[x,y,z],[sx,sy,sz],c).rotation.y=x*.5;
  const dark=new T.Mesh(new T.BoxGeometry(1,1,1),new T.MeshBasicMaterial({color:'#080605'}));dark.position.set(0,1.35,.2);dark.scale.set(2,2.7,.5);g.add(dark);
  for(const x of [-1.2,1.2])P(unit,[x,1.55,.55],[.34,3.1,.34],'#6b4524');P(unit,[0,3.2,.55],[3.1,.38,.44],'#7d5330');for(const x of [-.75,.75])P(unit,[x,3.2,.8],[.12,.5,.08],'#3b2614');
  const board=new T.Mesh(new T.PlaneGeometry(3.6,.9),new T.MeshBasicMaterial({map:minePortalSign('MINA DE LAS PALMAS',512,128,'bold 46px sans-serif','#3a2412')}));board.position.set(0,3.95,.8);g.add(board);
  const glow=new T.MeshBasicMaterial({color:'#ffcf6b'});for(const x of [-1.2,1.2]){const l=new T.Mesh(new T.IcosahedronGeometry(.2,1),glow);l.position.set(x,2.65,.85);g.add(l);}
  const light=new T.PointLight(0xffbe66,70,20,2);light.position.set(0,2.4,2);g.add(light);
  for(const x of [-.45,.45])P(unit,[x,.07,1.7],[.09,.07,2.6],'#545454');for(let i=0;i<4;i++)P(unit,[0,.04,.7+i*.7],[1.3,.06,.22],'#5a3b22');
  const ring=new T.Mesh(new T.RingGeometry(.9,1.25,32),new T.MeshBasicMaterial({color:'#ffd25e',transparent:true,opacity:.7,side:T.DoubleSide,depthWrite:false}));ring.rotation.x=-Math.PI/2;ring.position.set(0,.08,2);g.add(ring);
  const beamMat=new T.MeshBasicMaterial({color:'#ffcc55',transparent:true,opacity:.32,depthWrite:false});const beam=new T.Mesh(new T.CylinderGeometry(.28,.5,14,12,1,true),beamMat);beam.position.set(0,10,-.4);g.add(beam);
  beam.onBeforeRender=()=>{const t=performance.now()/600;beamMat.opacity=.22+.12*Math.sin(t);ring.material.opacity=.45+.3*Math.sin(t*1.6);};
  const tag=new T.Sprite(new T.SpriteMaterial({map:minePortalSign('⛏ MINA DE LAS PALMAS · ENTRAR',768,96,'bold 40px sans-serif','#2c1a0ce6'),depthTest:false,transparent:true}));tag.position.set(0,6.4,0);tag.scale.set(8,1,1);tag.renderOrder=5;g.add(tag);
 }
 function buildProp(g,key){g.clear();g.userData.key=key;const k=key||'';const P=(shape,pos,scale,c)=>part(g,shape,pos,scale,c);
 if(k.startsWith('tree')||k.startsWith('bush')){const bush=k.startsWith('bush'),stump=k.includes('stump');P(cylinder,[0,bush?.3:1.5,0],[bush?.15:.24,bush?.6:3,.24],'#71533c');if(stump){g.children[0].scale.y=.4;g.children[0].position.y=.2;return;}const base=bush?.7:3.4;for(let i=0;i<5;i++){const a=i*2.4;const m=P(orb,[Math.sin(a)*.9,base+Math.cos(a)*.4,Math.cos(a)*.8],[bush?.7:1.35,bush?.6:1.2,bush?.7:1.35],['#41634a','#547a4b','#6b8a50'][i%3]);m.rotation.y=a;}if(k.endsWith('_full'))for(let i=0;i<5;i++)P(orb,[Math.sin(i*2)*1.2,2.8+(i%2)*.6,Math.cos(i*2)*1.2],[.16,.16,.16],k.includes('manzana')?'#c65b46':'#e5b34d');
 }else if(k.startsWith('rock')){const m=P(orb,[0,.6,0],[1,.75,.85],k.includes('plata')?'#8d9b9d':k.includes('cobre')?'#b28a68':'#8a8c84');m.rotation.y=.8;if(!k.includes('depleted'))for(let i=0;i<3;i++)P(orb,[.5*Math.sin(i*2),.95,.5*Math.cos(i*2)],[.2,.18,.2],k.includes('plata')?'#d1dde0':'#cf9b60');
 }else if(k.startsWith('animal')){const bird=k.includes('ave'),rabbit=k.includes('conejo');const c=bird?'#d5b071':rabbit?'#ad9b86':'#967450';P(orb,[0,bird?.4:.65,0],[bird?.35:rabbit?.45:.7,bird?.3:.45,bird?.4:.4],c);P(orb,[.4,bird?.65:1.05,0],[.3,.3,.25],c);if(rabbit)for(const z of [-.13,.13])P(cone,[.45,1.5,z],[.13,.7,.13],c);if(!bird)for(const x of [-.4,.35])for(const z of [-.22,.22])P(cylinder,[x,.25,z],[.08,.5,.08],'#635744');
 }else if(k.startsWith('plot')){P(unit,[0,.08,0],[1.7,.16,1.7],'#76523b');for(let i=0;i<3;i++)P(unit,[-.6+i*.6,.18,0],[.1,.1,1.5],'#9b7450');if(k!=='plot_empty')for(let i=0;i<4;i++)P(orb,[(i%2)*.7-.35,.4,Math.floor(i/2)*.7-.35],[.3,k.includes('grown')?.6:.2,.3],'#67924c');
 }else if(k.startsWith('spot_')){const ring=new T.Mesh(geometry('ripple',()=>new T.TorusGeometry(.6,.04,5,24)),material(k.includes('oro')?'#d8b763':'#abd7d4'));ring.rotation.x=Math.PI/2;ring.position.y=.05;g.add(ring);
 }else if(k.startsWith('fuente')){P(cylinder,[0,.35,0],[2.2,.7,2.2],'#b2aea0');P(cylinder,[0,.72,0],[1.9,.08,1.9],'#76afb3');P(cylinder,[0,1.4,0],[.22,1.5,.22],'#cbc2ab');P(cylinder,[0,2,0],[.9,.18,.9],'#d1c5a7');
 }else if(k.startsWith('antorcha')||k==='lamp'){P(cylinder,[0,1.7,0],[.09,3.4,.09],'#353e3c');P(unit,[0,3.5,0],[.5,.7,.5],'#e4bb72');P(cone,[0,4.02,0],[.5,.35,.5],'#354039');
 }else if(k.includes('valla')||k.includes('baranda')){for(const x of [-.85,.85])P(unit,[x,.7,0],[.16,1.4,.16],'#846a4b');for(const y of [.5,1.1])P(unit,[0,y,0],[1.9,.12,.12],'#9d8060');if(k.includes('_v'))g.rotation.y=Math.PI/2;
 }else if(k.includes('puesto')){for(const x of [-1,1])for(const z of [-.5,.5])P(unit,[x,1.1,z],[.12,2.2,.12],'#68533c');P(unit,[0,.85,0],[2.4,.5,1.4],'#a38459');P(unit,[0,2.3,0],[2.8,.18,2],'#ce925f');for(let i=0;i<5;i++)P(orb,[-.9+i*.4,1.2,0],[.18,.18,.18],i%2?'#b9473a':'#d9b957');
 }else if(k.startsWith('cascada')){P(unit,[0,1,0],[12,2,2],'#7b8d82');P(unit,[0,1,1.1],[9,2,.2],'#9ac9ca');
 }else if(k==='mine_portal'){buildMinePortal(g,P);
 }else if(k.includes('mina')){P(orb,[0,1.6,0],[2.5,2,1.5],'#777e74');P(unit,[0,1.1,1.3],[1.6,2.2,.1],'#302e2a');
 }else if(k.includes('sign')){P(unit,[0,1,0],[.14,2,.14],'#6a533b');P(unit,[0,1.8,0],[2,.65,.2],'#b89b69');
 }else{P(orb,[0,.5,0],[.6,.6,.6],'#6c8350');}}
 function sprite(key,x,y,id){const g=new T.Group();g.position.set(x*2+1,height(x,y),y*2+1);g.userData.id=id;buildProp(g,key);scene.add(g);if(id){for(const m of g.children){m.userData.id=id;pick.push(m);}}return g;}
 // A continuous gabled roof with real eaves replaces the stretched pyramid.
 const roofCanvas=document.createElement('canvas');roofCanvas.width=roofCanvas.height=128;
 const roofCtx=roofCanvas.getContext('2d');roofCtx.fillStyle='#aa7155';roofCtx.fillRect(0,0,128,128);
 for(let row=0;row<4;row++)for(let col=0;col<4;col++){const x=col*32,y=row*32;roofCtx.fillStyle=(row+col)%3===0?'#b67e5e':'#a96e52';roofCtx.fillRect(x+1,y+1,30,30);roofCtx.strokeStyle='#85533e';roofCtx.lineWidth=2;roofCtx.beginPath();roofCtx.moveTo(x,y+31);roofCtx.lineTo(x+32,y+31);roofCtx.stroke();roofCtx.strokeStyle='#c4906c';roofCtx.lineWidth=2;roofCtx.beginPath();roofCtx.moveTo(x+9,y+2);roofCtx.lineTo(x+9,y+28);roofCtx.stroke();}
 const roofTexture=new T.CanvasTexture(roofCanvas);roofTexture.colorSpace=T.SRGBColorSpace;roofTexture.wrapS=roofTexture.wrapT=T.RepeatWrapping;roofTexture.anisotropy=4;
 const roofMaterial=new T.MeshLambertMaterial({map:roofTexture,color:'#ffffff',flatShading:true});
 function roofGeometry(width,depth,rise){
  const a=width/2+.32,b=depth/2+.32,positions=[],uv=[];
  const vertex=(p,u,v)=>{positions.push(...p);uv.push(u,v);};
  const A=[-a,0,b],B=[a,0,b],C=[0,rise,b],D=[-a,0,-b],E=[a,0,-b],F=[0,rise,-b];
  const length=depth/2,slope=Math.hypot(a,rise)/4;
  // Left and right roof slopes: shared ridge, no gaps or floating roof panels.
  for(const points of [[D,A,C,D,C,F],[B,E,F,B,F,C]])for(let i=0;i<points.length;i++){const p=points[i];vertex(p,(p[2]+b)/4,p[0]===0?slope:0);}
  for(const p of [A,B,C,D,F,E])vertex(p,(p[0]+a)/4,p[1]/4);
  const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(positions,3));geo.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geo.addGroup(0,12,0);geo.addGroup(12,6,1);geo.computeVertexNormals();return geo;
 }
 function gableRoof(x,y,z,width,depth,wallColor){
  const rise=Math.max(1.1,Math.min(2.5,width*.16));
  const geo=geometry(`gable:${width}:${depth}`,()=>roofGeometry(width,depth,rise));
  const roof=new T.Mesh(geo,[roofMaterial,material(wallColor)]);roof.position.set(x,y,z);roof.castShadow=true;roof.receiveShadow=true;scene.add(roof);
  // Fine fascia and a rounded terracotta ridge give the roof a finished edge.
  for(const dx of [-width/2-.29,width/2+.29])box(x+dx,y-.04,z,.12,.19,depth+.7,'#75513f');
  const ridge=new T.Mesh(geometry(`ridge:${depth}`,()=>new T.CylinderGeometry(.12,.12,depth+.7,8)),material('#b87c59'));ridge.rotation.x=Math.PI/2;ridge.position.set(x,y+rise+.025,z);ridge.castShadow=true;scene.add(ridge);
 }

 const dynamic=[];
 for(const d of W.decorations){if(d.type==='building'){house(d.x,d.y,d.w||3,d.h||3,4,'#bc875f');}else sprite(d.sprite||d.frames?.[0],d.x,d.y);}
 function house(x,y,w,d,h,c){const ground=height(x,y),cx=(x+w/2)*2,cz=(y+d/2)*2;box(cx,ground+h/2,cz,w*2,h,d*2,c);gableRoof(cx,ground+h,cz,w*2,d*2,c);for(let xx=0;xx<w;xx++)for(let level=0;level<Math.max(1,Math.floor(h/2.5));level++){for(const face of [-1,1])box((x+xx)*2+1,ground+1.5+level*2.3,cz+face*(d+.03),.7,1.25,.08,'#455653');}box(cx,ground+1,(y+d)*2+.08,1.1,2,.12,'#65503b');box(cx,ground+.2,(y+d)*2+.6,w*2+.6,.4,1.2,'#b9af98');}
 function church(x,y,w,d,brick){const ground=height(x,y);house(x,y,w,d,6,brick);const cx=(x+w/2)*2,front=(y+d)*2;box(cx,ground+7.2,front-2,3.4,14.4,3.4,brick);for(const h of [5,8.5,11.5]){box(cx,ground+h,front-.24,3.65,.25,3.65,'#d2b28d');for(const xx of [-.65,.65]){const arch=new T.Mesh(geometry('arch',()=>new T.CapsuleGeometry(.25,.9,4,8)),material('#49534d'));arch.position.set(cx+xx,ground+h-1,front-.12);arch.scale.z=.3;scene.add(arch);}}box(cx,ground+15.6,front-2,.13,2,.13,'#e2cda0');box(cx,ground+16,front-2,1.15,.12,.13,'#e2cda0');const clock=new T.Mesh(geometry('clock',()=>new T.CircleGeometry(.5,24)),material('#eee2bf'));clock.position.set(cx,ground+9.8,front-.25);scene.add(clock);box(cx,ground+9.95,front-.2,.06,.35,.05,'#4c4d40');box(cx+.13,ground+9.8,front-.2,.3,.05,.05,'#4c4d40');}
 function santaGertrudis(d){
  const y=height(d.x,d.y),cx=(d.x+d.w/2)*2,front=(d.y+d.h)*2;
  const white='#f3f1e9',trim='#d9d6cb';
  house(d.x,d.y,d.w,d.h,6.3,white);
  // Twin white bell towers, terracotta domes, classical portico and pediment.
  for(const dx of [-7.5,7.5]){
   box(cx+dx,y+7,front-2.5,4,14,4,white);
   for(const h of [4.5,8.2,11,13.7])box(cx+dx,y+h,front-2.5,4.35,.28,4.35,trim);
   for(const h of [9.5,12.1]){const arch=new T.Mesh(new T.CapsuleGeometry(.52,1.1,4,10),material('#52544d'));arch.scale.z=.12;arch.position.set(cx+dx,y+h,front-.45);scene.add(arch);}
   const dome=new T.Mesh(new T.SphereGeometry(2.05,20,10,0,Math.PI*2,0,Math.PI/2),material('#a2644c'));dome.position.set(cx+dx,y+14,front-2.5);scene.add(dome);
   box(cx+dx,y+17,front-2.5,.13,2,.13,'#80765f');box(cx+dx,y+17.3,front-2.5,1,.13,.13,'#80765f');
   const clock=new T.Mesh(new T.CircleGeometry(.65,24),material('#fff8dc'));clock.position.set(cx+dx,y+7,front-.44);scene.add(clock);box(cx+dx,y+7.18,front-.39,.07,.45,.05,'#454940');box(cx+dx+.15,y+7,front-.38,.36,.07,.05,'#454940');
  }
  box(cx,y+3.6,front-.9,11,7.2,1,white);
  for(const dx of [-3.5,0,3.5]){const door=new T.Mesh(new T.CapsuleGeometry(.65,1.7,4,12),material('#6c5540'));door.scale.z=.15;door.position.set(cx+dx,y+1.8,front-.32);scene.add(door);}
  for(const dx of [-5,-3.3,3.3,5]){const column=new T.Mesh(new T.CylinderGeometry(.26,.32,5.2,12),material(white));column.position.set(cx+dx,y+2.9,front+.5);scene.add(column);box(cx+dx,y+.35,front+.5,.85,.5,.85,trim);box(cx+dx,y+5.5,front+.5,.8,.35,.8,trim);}
  box(cx,y+5.9,front+.4,12,.55,2.2,white);
  const shape=new T.Shape();shape.moveTo(-6,0);shape.lineTo(6,0);shape.lineTo(0,3);shape.closePath();const pediment=new T.Mesh(new T.ExtrudeGeometry(shape,{depth:.6,bevelEnabled:false}),material(white));pediment.position.set(cx,y+6.2,front+.5);scene.add(pediment);
  for(let i=0;i<3;i++)box(cx,y+.15+i*.15,front+1.5-i*.35,13,.25,2-i*.3,trim);
 }

 // Church landmark remains beside the original plaza and capataz house.
 church(102,12,3,3,'#ba805c');
 function santaAna(d){
  const y=height(d.x,d.y),cx=(d.x+d.w/2)*2,front=(d.y+d.h)*2,cz=(d.y+d.h/2)*2;
  const cream='#f0eadc',trim='#cdb68f';
  box(cx,y+4,cz,d.w*2,8,d.h*2,cream);gableRoof(cx,y+8.1,cz,d.w*2,d.h*2,cream);
  function arch(x,bottom,z,w,h,c){const shape=new T.Shape();shape.moveTo(-w/2,0);shape.lineTo(w/2,0);shape.lineTo(w/2,h-w/2);shape.absarc(0,h-w/2,w/2,0,Math.PI,false);shape.closePath();const m=new T.Mesh(new T.ShapeGeometry(shape),material(c));m.position.set(x,bottom,z);scene.add(m);}
  for(const dx of [-7,0,7]){box(cx+dx,y+2.5,front+.06,4.3,5.2,.2,trim);arch(cx+dx,y+.3,front+(dx===0?.55:.19),dx===0?2.7:2.1,4.3,'#4c493f');for(const ex of [-2,2])box(cx+dx+ex,y+3,front+.3,.35,6,.45,cream);}
  box(cx,y+9,front-2,4.8,18,4.8,cream);
  for(const h of [5.7,8.2,12.8,16.9])box(cx,y+h,front-2,5.3,.3,5.3,trim);
  for(const dx of [-1,1])arch(cx+dx,y+13.4,front+.43,.8,2.3,'#505c54');
  const clock=new T.Mesh(new T.CircleGeometry(.95,32),material('#f8f0d7'));clock.position.set(cx,y+10.6,front+.43);scene.add(clock);box(cx,y+10.8,front+.47,.08,.6,.05,'#534c3c');box(cx+.2,y+10.6,front+.47,.5,.08,.05,'#534c3c');
  const cap=new T.Mesh(new T.ConeGeometry(3.9,3.8,4),material('#ad775a'));cap.rotation.y=Math.PI/4;cap.position.set(cx,y+19.9,front-2);scene.add(cap);
  box(cx,y+23,front-2,.18,2.4,.18,'#f1dfab');box(cx,y+23.4,front-2,1.4,.18,.18,'#f1dfab');
  for(let i=0;i<4;i++)box(cx,y+.08+i*.13,front+1.8-i*.35,d.w*2+2-i*.6,.17,3.2-i*.4,'#b9b3a0');
 }
 for(const d of W.landmarks){if(d.kind==='santa_gertrudis')santaGertrudis(d);else if(d.kind==='santa_ana')santaAna(d);else if(d.kind==='basilica')church(d.x,d.y,d.w,d.h,d.color);else house(d.x,d.y,d.w,d.h,d.height,d.color);}
 // Bronze head inspired by the supplied sculpture reference.
 {const park=(W.parkDetails||[]).find(p=>p.id==='poblado');const x=park?park.x:2+(W.expansion?.offsetX||0),z=park?park.y:14+(W.expansion?.offsetY||0),y=height(x,z);const g=new T.Group();g.position.set(x*2+1,y,z*2+1);scene.add(g);
 const bronze=new T.MeshStandardMaterial({color:'#9b6136',metalness:.65,roughness:.32});
 const part=(geo,px,py,pz,scale=[1,1,1],mat=bronze)=>{const m=new T.Mesh(geo,mat);m.position.set(px,py,pz);m.scale.set(...scale);m.castShadow=true;g.add(m);return m;};
 part(new T.BoxGeometry(3.4,1.2,2.8),0,.6,0,[1,1,1],material('#c5ac83'));part(new T.SphereGeometry(1.5,32,24),0,2.65,0,[1,1.08,.8]);
 for(const side of [-1,1]){part(new T.SphereGeometry(.4,16,8),side*.64,2.95,1.03,[1,.23,.35]);part(new T.SphereGeometry(.26,16,8),side*.6,2.8,1.12,[1,.3,.2],material('#291a12'));}
 part(new T.CylinderGeometry(.13,.18,.85,12),0,2.85,1.2);part(new T.SphereGeometry(.28,16,12),0,2.48,1.37,[1,.85,.8]);
 part(new T.TorusGeometry(.42,.1,8,28,Math.PI),0,2.04,1.06,[1,.5,1]);const lip=part(new T.TorusGeometry(.4,.1,8,28,Math.PI),0,1.93,1.07,[1,.65,1]);lip.rotation.z=Math.PI;
 }
 for(const n of (initialZone?api.cityNodes.values():S.nodes.values())){if(n.def.type==='home_door')continue;const sp=sprite(api.spriteKeyFor(n),n.def.x,n.def.y,n.def.id);if(sp)dynamic.push({sp,n});}
 for(const a of (initialZone?api.cityAnimals:S.animals)){const sp=sprite(a.def.sprites.alive[0],a.fx,a.fy,a.def.id);if(sp)dynamic.push({sp,a});}
 for(const d of W.doors){const m=box(d.x*2+1,height(d.x,d.y)+1,d.y*2+1,1.4,2,.3,'#684b2e');m.userData.id=d.id;pick.push(m);}
 const cityLighting=enrichWorld(T,scene,W,pick,height,material);status.lamps=cityLighting.count;
 for(const road of W.roads3d||[]){
  for(let i=0;i<road.points.length-1;i++){
   const a=road.points[i],b=road.points[i+1],dx=b.x-a.x,dz=b.y-a.y,length=Math.hypot(dx,dz),nx=-dz/length,nz=dx/length;
   for(let d=1;d<length;d+=3){const t=d/length,x=(a.x+dx*t)*2+1,z=(a.y+dz*t)*2+1,y=height(a.x+dx*t,a.y+dz*t)+.1;
    const dash=box(x,y,z,.13,.04,2.4,'#f1d683');dash.quaternion.setFromUnitVectors(new T.Vector3(0,0,1),new T.Vector3(dx*2,b.height-a.height,dz*2).normalize());
    for(const side of [-1,1]){const gx=x+nx*5.1*side,gz=z+nz*5.1*side,gy=height(gx/2,gz/2);box(gx,gy+.65,gz,.12,1.3,.12,'#aeb6b1');const rail=box(gx,gy+1.1,gz,.12,.18,6.3,'#bec4bd');rail.rotation.y=Math.atan2(dx,dz);}
   }
  }
 }

 const underground=buildMine(T,W);
 buildHomeMarker(T,scene,pick,height,material);
 const casaView=buildHouse(T);status.rebuildHouse=(layout)=>casaView.rebuild(layout||window.Casa.layout);
 function doorHit(list){return !!(list && (list.exitDoor || list.id==='puerta_salida'));}
 const indoors=()=>W.mapId==='mine'||W.mapId==='casa';
 const activeScene=()=>W.mapId==='mine'?underground.scene:W.mapId==='casa'?casaView.scene:scene;
 const activePick=()=>W.mapId==='mine'?underground.pick:W.mapId==='casa'?casaView.pick:pick;
 const actorMap=new Map();
 const speechLayer=document.createElement('div');speechLayer.id='speech-layer';speechLayer.style.cssText='position:fixed;inset:0;pointer-events:none;z-index:2;overflow:hidden';document.body.append(speechLayer);
 const floatLabels=new Map();const speech=new Map(),projected=new T.Vector3();
 const playerNames=new Map();
 function drawPlayerNames(){
  for(const [id,el] of playerNames)if(!S.others.has(id)){el.remove();playerNames.delete(id);}
  for(const [id,p] of S.others){
   let el=playerNames.get(id);if(!el){el=document.createElement('div');el.className='player-name';speechLayer.append(el);playerNames.set(id,el);}
   el.textContent=p.name;el.classList.toggle('bot-name',!!p.bot);
   const a=actorMap.get('peer'+id);if(!a){el.hidden=true;continue;}
   projected.copy(a.position);projected.y+=2.7;projected.project(camera);
   el.hidden=!api.started||projected.z< -1||projected.z>1||Math.abs(projected.x)>1.1||Math.abs(projected.y)>1.1;
   el.style.left=((projected.x+1)*innerWidth/2)+'px';el.style.top=((1-projected.y)*innerHeight/2)+'px';
  }
  const count=[...S.others.values()].filter(p=>!p.bot).length+(S.net.ok?1:0);
  const label=S.net.ok?'En línea: '+count:'Reconectando…';const b=document.querySelector('#online-players');if(b.textContent!==label)b.textContent=label;
 }

 function drawSpeech(){for(const [f,el] of floatLabels){if(!S.floaters.includes(f)){el.remove();floatLabels.delete(f);}}for(const f of S.floaters){let el=floatLabels.get(f);if(!el){el=document.createElement('div');el.className='world-reward';el.textContent=f.text;el.style.color=f.color;speechLayer.append(el);floatLabels.set(f,el);}const x=f.x/64,y=f.y/64;projected.set(x*2,height(x,y)+3+(api.now()-f.t0)/1000,y*2+1).project(camera);el.hidden=projected.z< -1||projected.z>1;el.style.left=((projected.x+1)*innerWidth/2)+'px';el.style.top=((1-projected.y)*innerHeight/2)+'px';}speechLayer.hidden=!status.active||!api.started;for(const [id,el] of speech){if(!S.bubbles.has(id)){el.remove();speech.delete(id);}}
 for(const [id,b] of S.bubbles){let el=speech.get(id);if(!el){el=document.createElement('div');el.className='character-speech';speechLayer.append(el);speech.set(id,el);}el.textContent=b.text;const a=actorMap.get(id===0?'self':'peer'+id);if(!a){el.hidden=true;continue;}projected.copy(a.position);projected.y+=3;projected.project(camera);el.hidden=!api.started||projected.z< -1||projected.z>1||Math.abs(projected.x)>1||Math.abs(projected.y)>1;el.style.left=((projected.x+1)*innerWidth/2)+'px';el.style.top=((1-projected.y)*innerHeight/2)+'px';}}

 function actor(id,x,y,color){let g=actorMap.get(id);if(!g){g=new T.Group();const body=new T.Mesh(new T.BoxGeometry(.7,1,.45),material(color||'#467eb1'));body.position.y=1;g.add(body);const head=new T.Mesh(new T.BoxGeometry(.5,.5,.5),material('#d0a47c'));head.position.y=1.8;g.add(head);for(const dx of [-.22,.22]){const leg=new T.Mesh(new T.BoxGeometry(.25,.6,.3),material('#4b4132'));leg.position.set(dx,.3,0);g.add(leg);}for(const dx of [-.5,.5]){const arm=new T.Mesh(new T.BoxGeometry(.2,.65,.22),material(color||'#467eb1'));arm.position.set(dx,1.05,0);g.add(arm);}const hair=new T.Mesh(new T.BoxGeometry(.53,.17,.53),material('#564334'));hair.position.set(0,2.03,0);g.add(hair);g.traverse(m=>{if(m.isMesh){m.castShadow=true;m.receiveShadow=true;}});scene.add(g);actorMap.set(id,g);}g.position.set(x*2+1,height(x,y),y*2+1);return g;}
 for(const n of W.npcs){const a=actor(n.id,n.x,n.y,'#ab8338');a.userData.id=n.id;a.children.forEach(m=>{m.userData.id=n.id;pick.push(m);});}
 const style=document.createElement('style');style.textContent=`#juego{visibility:hidden}#world-tools{position:fixed;left:12px;top:180px;z-index:12;display:flex;gap:5px;max-width:90vw;flex-wrap:wrap}#world-tools button,#memories button{background:#302b22;color:#f1d69d;border:1px solid #b39153;border-radius:5px;padding:9px;font:14px sans-serif}#world-note{position:fixed;top:224px;left:12px;color:#fff3cc;text-shadow:1px 1px #222;font:12px sans-serif;max-width:240px;pointer-events:none}#memories{position:fixed;z-index:40;left:50%;top:50%;transform:translate(-50%,-50%);width:min(550px,88vw);max-height:70vh;overflow:auto;background:#29271f;color:#f4e6c8;border:2px solid #aa8c53;padding:18px;font:15px/1.5 sans-serif}#memories a{color:#d6b467}#memories article{border-top:1px solid #766447;padding:10px 0}#memories h3{margin:4px 0}#memories p{margin:6px 0}#touch-walk{position:fixed;right:12px;bottom:92px;z-index:15;display:grid;grid-template-columns:repeat(3,40px);gap:3px}#touch-walk button{height:40px;background:#332c22cc;color:#f0d5a3;border:1px solid #a18855;touch-action:none} @media(min-width:900px){#touch-walk{display:none}}@media(max-width:600px){#world-tools{top:146px;max-width:230px}#world-tools button{padding:7px;font-size:12px}#world-note{top:215px;font-size:11px}#hud-mapa{transform:scale(.7);transform-origin:top right}#hud-derecha{top:260px;max-width:180px}}`;
 document.head.append(style);
 const tools=document.createElement('div');tools.id='world-tools';tools.innerHTML='<button id="book">Memorias 0/4</button><button id="camera-home">Centrar</button><button id="camera-settings" aria-expanded="false" aria-controls="camera-panel">Cámara 360°</button><button id="zoom-in" aria-label="Acercar">＋</button><button id="zoom-out" aria-label="Alejar">−</button><button id="route-open">Recorrer SaimonCity</button><button id="online-players" aria-label="Ver jugadores conectados">Conectando…</button>';document.body.append(tools);document.querySelector('#online-players').onclick=()=>document.querySelector('#b-soc').click();
 const note=document.createElement('div');note.id='world-note';note.textContent='Vista desde arriba · Joystick o WASD: caminar · Arrastra: azimut 360° e inclinación · Cámara: ajustar cenit · Pellizca: zoom\nMundo interpretado · '+BUILD;document.body.append(note);
 const panel=document.createElement('section');panel.id='memories';panel.hidden=true;document.body.append(panel);
 let found;try{found=new Set(JSON.parse(localStorage.getItem('lifeinc.aburra.memories.v1')||'[]'));}catch{found=new Set();}
 function journal(){panel.replaceChildren();const close=document.createElement('button');close.textContent='Cerrar';close.onclick=()=>panel.hidden=true;panel.append(close);const title=document.createElement('h2');title.textContent='Memorias del Valle de Aburrá';panel.append(title);for(const m of W.memories){const a=document.createElement('article');const h=document.createElement('h3');h.textContent=(found.has(m.id)?'✓ ':'◇ ')+m.name;const p=document.createElement('p');p.textContent=found.has(m.id)?m.text:`Acércate al marcador dorado (${m.x}, ${m.y}) para descubrir esta memoria.`;a.append(h,p);if(found.has(m.id)){const link=document.createElement('a');link.href=m.source;link.target='_blank';link.rel='noopener';link.textContent='Consultar fuente histórica';a.append(link);}panel.append(a);}panel.hidden=false;}
 document.querySelector('#book').onclick=journal;
 const cameraPanel=document.createElement('section');cameraPanel.id='camera-panel';cameraPanel.hidden=true;cameraPanel.setAttribute('aria-label','Ajustes de cámara');cameraPanel.innerHTML='<header>Cámara orbital <button id="camera-close" aria-label="Cerrar ajustes de cámara">×</button></header><label for="camera-azimuth">Azimut · giro horizontal</label><div class="camera-value"><input id="camera-azimuth" type="range" min="0" max="360" step="1" aria-label="Deslizar azimut"><input id="camera-azimuth-value" type="number" min="0" max="360" step="1" aria-label="Azimut en grados"><span>°</span></div><label for="camera-zenith">Ángulo cenital · inclinación</label><div class="camera-value"><input id="camera-zenith" type="range" min="0" max="80" step="1" aria-label="Deslizar ángulo cenital"><input id="camera-zenith-value" type="number" min="0" max="80" step="1" aria-label="Ángulo cenital en grados"><span>°</span></div><p>0°: desde arriba · 80°: vista baja.<br>Arrastra para girar e inclinar. Shift + flechas también ajusta la cámara.</p>';document.body.append(cameraPanel);
 const cameraCSS=document.createElement('style');cameraCSS.textContent='#camera-panel{position:fixed;left:12px;top:270px;z-index:23;width:min(300px,calc(100vw - 24px));max-height:calc(100dvh - 290px);overflow:auto;box-sizing:border-box;padding:12px;background:#241c14f5;border:1px solid #ad8951;border-radius:10px;box-shadow:0 8px 25px #0008;color:#f6e2bd;font:13px/1.5 system-ui}#camera-panel[hidden]{display:none}#camera-panel header{display:flex;align-items:center;justify-content:space-between;font-weight:bold;margin-bottom:12px}#camera-panel button{background:#594128;border:1px solid #ab8650;color:#ffe4b2;border-radius:5px;min-width:32px;min-height:32px;cursor:pointer}#camera-panel label{display:block;margin-top:10px}.camera-value{display:flex;align-items:center;gap:8px}.camera-value input[type=range]{min-width:0;flex:1;accent-color:#e2b769}.camera-value input[type=number]{width:54px;padding:6px 3px;background:#392a1c;color:#ffe6b7;border:1px solid #8f6e40;border-radius:4px;font:14px system-ui}#camera-panel p{font-size:11px;color:#c6b698;margin-bottom:0}body:not(.in-game) #camera-panel,.solo-mundo #camera-panel{display:none!important}@media(max-width:600px){#camera-panel{top:260px;max-height:calc(100dvh - 280px)}}';document.head.append(cameraCSS);
 const azimuthRange=document.getElementById('camera-azimuth'),azimuthValue=document.getElementById('camera-azimuth-value'),zenithRange=document.getElementById('camera-zenith'),zenithValue=document.getElementById('camera-zenith-value');
 const setCameraPanel=open=>{cameraPanel.hidden=!open;document.getElementById('camera-settings').setAttribute('aria-expanded',String(open));};
 document.getElementById('camera-settings').onclick=()=>setCameraPanel(cameraPanel.hidden);document.getElementById('camera-close').onclick=()=>setCameraPanel(false);
 function syncCameraControls(){const az=Math.round(clampYaw(yaw)*180/Math.PI)%360,zen=Math.round(90-pitch*180/Math.PI);for(const [input,value] of [[azimuthRange,az],[azimuthValue,az],[zenithRange,zen],[zenithValue,zen]])if(document.activeElement!==input&&input.value!==String(value))input.value=value;}
 for(const input of [azimuthRange,azimuthValue])input.oninput=()=>{if(input.value===''||!Number.isFinite(Number(input.value)))return;yaw=clampYaw(Math.max(0,Math.min(360,Number(input.value)))*Math.PI/180);syncCameraControls();};
 for(const input of [zenithRange,zenithValue])input.oninput=()=>{if(input.value===''||!Number.isFinite(Number(input.value)))return;pitch=(90-Math.max(0,Math.min(80,Number(input.value))))*Math.PI/180;syncCameraControls();};
 document.querySelector('#camera-home').onclick=()=>{yaw=.45;pitch=1.12;distance=36;syncCameraControls();};

 document.querySelector('#zoom-in').onclick=()=>distance=Math.max(10,distance-7);
 document.querySelector('#zoom-out').onclick=()=>distance=Math.min(110,distance+7);
 const joystick=document.createElement('div');joystick.id='city-joystick';joystick.setAttribute('role','group');joystick.setAttribute('aria-label','Joystick para caminar');joystick.innerHTML='<span></span>';document.body.append(joystick);const knob=joystick.firstChild;
 const joyStyle=document.createElement('style');joyStyle.textContent='#city-joystick{position:fixed;left:max(16px,env(safe-area-inset-left));bottom:max(88px,env(safe-area-inset-bottom));width:96px;height:96px;border-radius:50%;border:1px solid #ffe3a56b;background:#15201840;z-index:16;touch-action:none;opacity:.55}#city-joystick span{position:absolute;left:30px;top:30px;width:36px;height:36px;border-radius:50%;background:#ffe3a5a0;pointer-events:none}#city-joystick:active{opacity:1}body:not(.in-game) #city-joystick{display:none}';document.head.append(joyStyle);
 let joyPointer=null;const resetStick=()=>{stickX=stickY=0;joyPointer=null;S.keys.delete('joystick');knob.style.transform='';};
 const moveStick=e=>{const r=joystick.getBoundingClientRect(),dx=e.clientX-r.left-r.width/2,dy=e.clientY-r.top-r.height/2,len=Math.hypot(dx,dy),scale=Math.min(1,30/(len||1));knob.style.transform=`translate(${dx*scale}px,${dy*scale}px)`;stickX=len>12?Math.round(dx/len):0;stickY=len>12?Math.round(dy/len):0;if(stickX||stickY)S.keys.add('joystick');else S.keys.delete('joystick');};
 joystick.onpointerdown=e=>{if(!api.started||joyPointer!==null)return;e.preventDefault();joyPointer=e.pointerId;joystick.setPointerCapture(e.pointerId);S.player.path=[];S.player.pending=null;S.dest=null;moveStick(e);};joystick.onpointermove=e=>{if(e.pointerId===joyPointer)moveStick(e);};joystick.onpointerup=joystick.onpointercancel=joystick.onlostpointercapture=e=>{if(e.pointerId===joyPointer)resetStick();};addEventListener('blur',resetStick);document.addEventListener('visibilitychange',resetStick);
 const routes=document.createElement('section');routes.id='world-routes';routes.hidden=true;routes.innerHTML='<header>Destinos <button id="route-close" aria-label="Cerrar destinos">×</button></header><p>Elige un destino para caminar hasta allí. Toca el suelo para cambiar de camino.</p>';for(const d of W.waypoints){const b=document.createElement('button');b.textContent=d.name;b.onclick=()=>{if(api.started){if(d.id==='las_palmas')api.followRoad('las_palmas');else api.goTo(d.x,d.y);distance=d.id==='sabaneta'?70:d.id==='las_palmas'?52:44;routes.hidden=true;}};routes.append(b);}document.body.append(routes);document.querySelector('#route-open').onclick=()=>routes.hidden=!routes.hidden;document.querySelector('#route-close').onclick=()=>routes.hidden=true;
 addEventListener('blur',()=>S.keys.clear());

 for(const m of W.memories){const mesh=new T.Mesh(new T.OctahedronGeometry(.65),material('#edc76b'));mesh.position.set(m.x*2+1,height(m.x,m.y)+2.5,m.y*2+1);mesh.userData.memory=m;scene.add(mesh);pick.push(mesh);m.mesh=mesh;}
 let touches=new Map(),down=null,drag=false,pinch=0;
 cv.onpointerdown=e=>{cv.setPointerCapture(e.pointerId);touches.set(e.pointerId,[e.clientX,e.clientY]);down=[e.clientX,e.clientY];drag=false;pinch=0;};
 cv.onpointermove=e=>{const hovering=()=>{if(W.mapId!=='casa'||drag){cv.style.cursor='';casaView.setDoorHover(false);return;}pointer.set(e.clientX/innerWidth*2-1,1-e.clientY/innerHeight*2);ray.setFromCamera(pointer,camera);const over=doorHit(ray.intersectObjects(activePick(),false)[0]?.object.userData);cv.style.cursor=over?'pointer':'';casaView.setDoorHover(over);};if(!touches.has(e.pointerId)){hovering();return;}const prev=touches.get(e.pointerId);touches.set(e.pointerId,[e.clientX,e.clientY]);if(touches.size>1){const [a,b]=[...touches.values()];const d=Math.hypot(a[0]-b[0],a[1]-b[1]);if(pinch)distance=Math.max(10,Math.min(110,distance*pinch/d));pinch=d;drag=true;}else{if(down&&Math.hypot(e.clientX-down[0],e.clientY-down[1])>6)drag=true;if(drag){yaw=clampYaw(yaw-(e.clientX-prev[0])*.008);pitch=Math.max(PITCH_MIN,Math.min(PITCH_MAX,pitch+(e.clientY-prev[1])*.005));}}hovering();};
 cv.onpointerup=e=>{touches.delete(e.pointerId);if(!drag&&api.started){pointer.set(e.clientX/innerWidth*2-1,1-e.clientY/innerHeight*2);ray.setFromCamera(pointer,camera);const hit=ray.intersectObjects(activePick(),false)[0];if(hit&&doorHit(hit.object.userData)){cv.style.cursor='';casaView.setDoorHover(false);api.exitHouse();return;}if(W.mapId==='casa'&&window.Casa?.editing){if(hit)window.Casa.clickTile(Math.floor(hit.point.x/2),Math.floor(hit.point.z/2),hit.object.userData.casaItem||null);return;}if(hit){const d=hit.object.userData;if(d.id)api.interact(d.id);else if(d.memory){api.goTo(d.memory.x,d.memory.y);}else if(!d.casaItem){const x=Math.floor(hit.point.x/2),y=Math.floor(hit.point.z/2);if(api.walkable(x,y))api.goTo(x,y);}}}};cv.onpointercancel=e=>{touches.delete(e.pointerId);drag=true;};cv.onwheel=e=>{e.preventDefault();distance=Math.max(10,Math.min(110,distance+Math.sign(e.deltaY)*3));};cv.oncontextmenu=e=>e.preventDefault();
 api.furnaceAtScreen=(x,y)=>{if(!api.started)return null;pointer.set(x/innerWidth*2-1,1-y/innerHeight*2);ray.setFromCamera(pointer,camera);const hit=ray.intersectObjects(activePick(),false)[0],id=hit?.object.userData.id;return id&&S.nodes.get(id)?.def.type==='furnace'?id:null;};
 const dropHalo=new T.Mesh(new T.RingGeometry(2.3,2.6,48),new T.MeshBasicMaterial({color:0xffd369,transparent:true,opacity:.9,depthWrite:false,side:T.DoubleSide}));dropHalo.rotation.x=-Math.PI/2;dropHalo.visible=false;
 function resize(){renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();}addEventListener('resize',resize);
 const colors={azul:'#376fc2',rojo:'#a33d30',verde:'#43843d',amarillo:'#d1aa36',morado:'#8858a5'};let color='';
 function updateTilt(dt){pitch=Math.max(PITCH_MIN,Math.min(PITCH_MAX,pitch+((turning.has('ArrowUp')?1:0)-(turning.has('ArrowDown')?1:0))*dt*.8));}
 function frame(){requestAnimationFrame(frame);const time=performance.now(),dt=Math.min(.05,(time-lastFrame)/1000);lastFrame=time;if(!status.active)return;if(editing()){turning.clear();zoomKeys.clear();zoomHeld=false;}updateZoom(dt);updateTilt(dt);yaw=clampYaw(yaw+((turning.has('ArrowRight')?1:0)-(turning.has('ArrowLeft')?1:0))*dt*1.8);if(!api.started){resetStick();setCameraPanel(false);}const p=S.player;if(W.mapId==='casa'){if(!status._casaCam){yaw=Math.PI-0.28;pitch=0.72;distance=15;status._casaCam=true;}}else if(status._casaCam){status._casaCam=false;yaw=.45;pitch=1.12;distance=36;}if(status.lookAt){const dx=status.lookAt.x-p.fx,dz=status.lookAt.y-p.fy;yaw=Math.atan2(-dx,-dz);pitch=1.02;distance=40;status.lookAt=null;}const me=actor('self',p.fx,p.fy,colors[S.me.color]);const view=activeScene();if(me.parent!==view)view.add(me);
 if(!me.userData.pica){const tool=new T.Group();const handle=new T.Mesh(new T.CylinderGeometry(.045,.045,1.4,8),material('#90643c'));tool.add(handle);const head=new T.Mesh(new T.BoxGeometry(.9,.14,.15),material('#bdc7c9'));head.position.y=.6;tool.add(head);tool.position.set(.6,1,.2);me.add(tool);me.userData.pica=tool;}const tool=me.userData.pica;tool.visible=api.now()<(p.miningUntil||0);tool.rotation.z=-.7+Math.sin(time*.025)*.9;
 if(color!==S.me.color){me.children[0].material=material(colors[S.me.color]||colors.azul);color=S.me.color;}me.rotation.y={up:Math.PI,down:0,left:-Math.PI/2,right:Math.PI/2}[p.dir]||0;
 const away=indoors();const live=new Set(['self',...(away?[]:W.npcs.map(n=>n.id))]);if(!away)for(const [id,o] of S.others){if(o.zone==='casa')continue;live.add('peer'+id);const peer=actor('peer'+id,o.fx,o.fy,colors[o.color]);peer.rotation.y={up:Math.PI,down:0,left:-Math.PI/2,right:Math.PI/2}[o.dir]||0;}for(const [id,a] of actorMap)if(!live.has(id)){if(away&&!String(id).startsWith('peer'))continue;(a.parent||scene).remove(a);actorMap.delete(id);}
 for(const d of (away?[]:dynamic)){const {sp,n,a}=d;if(n){const key=api.spriteKeyFor(n);if(key!==sp.userData.key){const meshes=sp.children.slice();for(const m of meshes){const i=pick.indexOf(m);if(i>=0)pick.splice(i,1);}buildProp(sp,key);for(const m of sp.children){m.userData.id=sp.userData.id;pick.push(m);}}}if(a){sp.visible=a.state==='alive';sp.position.set(a.fx*2+1,height(a.fx,a.fy),a.fy*2+1);}}
 const dropFurnace=api.draggedMineral?[...S.nodes.values()].find(n=>n.def.type==='furnace'):null;dropHalo.visible=!!dropFurnace;if(dropFurnace){if(dropHalo.parent!==view)view.add(dropHalo);dropHalo.position.set(dropFurnace.def.x*2+1,.09,dropFurnace.def.y*2+1);dropHalo.material.color.set(api.oreDropHovered?'#97ffb0':'#ffd369');}
 target.set(p.fx*2+1,height(p.fx,p.fy)+1,p.fy*2+1);camera.position.set(target.x+Math.sin(yaw)*Math.cos(pitch)*distance,target.y+Math.sin(pitch)*distance,target.z+Math.cos(yaw)*Math.cos(pitch)*distance);camera.up.set(-Math.sin(yaw)*Math.sin(pitch),Math.cos(pitch),-Math.cos(yaw)*Math.sin(pitch));camera.lookAt(target);syncCameraControls();
 sun.position.set(target.x-25,target.y+65,target.z+22);sun.target.position.copy(target);sun.intensity=S.night?.12:2.2;ambient.intensity=S.night?.28:2;ambient.color.set(S.night?'#8ca8dd':'#ffefd3');ambient.groundColor.set(S.night?'#182332':'#405336');scene.background.set(S.night?'#080f1c':'#a4c4bc');scene.fog.color.copy(scene.background);cityLighting.update(S.night,target);
 for(const id of ['route-open','book','hud-mapa'])document.getElementById(id).disabled=away;document.querySelector('#mine-route').textContent=W.mapId==='mine'?'♨ Horno central':'⛏ Mina de Las Palmas';
 const region=W.regions.find(r=>p.fx>=r.x&&p.fx<r.x+r.w&&p.fy>=r.y&&p.fy<r.y+r.h);document.querySelector('#zona-nombre').textContent=W.mapId==='casa'?'Tu casa · Medellín':region?.name||'Valle de Aburrá';
 for(const n of W.npcs)actor(n.id,n.x,n.y,'#ab8338');
 for(const m of W.memories){m.mesh.rotation.y+=.01;m.mesh.visible=!found.has(m.id);if(api.started&&!found.has(m.id)&&Math.hypot(p.fx-m.x,p.fy-m.y)<2){found.add(m.id);localStorage.setItem('lifeinc.aburra.memories.v1',JSON.stringify([...found]));document.querySelector('#book').style.outline='2px solid #edc76b';}}
 document.querySelector('#book').textContent=W.mapId==='mine'?'Mina de Las Palmas':W.mapId==='casa'?'Tu casa':`Memorias ${found.size}/${W.memories.length}`;camera.updateMatrixWorld();drawSpeech();drawPlayerNames();if(W.mapId==='casa'){projected.set(9,2.6,17.5).project(camera);status.doorScreen={x:(projected.x+1)*innerWidth/2,y:(1-projected.y)*innerHeight/2,z:projected.z};}underground.update(S,api.now());renderer.render(view,camera);status.frames=(status.frames||0)+1;status.zone=W.mapId||'city';status.camera={yaw,pitch,distance};
 }
 if(initialZone){Object.assign(W,savedZone);W.mapId=initialZone;}
 status.active=true;status.regions=W.regions.map(r=>r.id);status.ready=true;frame();
}
