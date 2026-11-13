/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Independent underground map, built from the same collision grid used by movement.
export function buildMine(T,W){
 const map=W.caveDefinition,scene=new T.Scene();scene.background=new T.Color('#130e0b');scene.fog=new T.Fog('#1c130e',38,100);scene.add(new T.HemisphereLight(0xe6bf83,0x503c27,.95));const fill=new T.DirectionalLight(0xe4c79b,.75);fill.position.set(20,45,25);scene.add(fill);
 const pick=[],resources=new Map(),materials=new Map();const mat=c=>{if(!materials.has(c))materials.set(c,new T.MeshLambertMaterial({color:c,flatShading:true}));return materials.get(c);};
 const boxGeo=new T.BoxGeometry(1,1,1),rockGeo=new T.IcosahedronGeometry(1,1);
 function mesh(geo,color,x,y,z,sx=1,sy=1,sz=1){const m=new T.Mesh(geo,typeof color==='string'?mat(color):color);m.position.set(x,y,z);m.scale.set(sx,sy,sz);m.receiveShadow=true;scene.add(m);return m;}
 function box(x,y,z,w,h,d,c){return mesh(boxGeo,c,x,y,z,w,h,d);}
 function label(text,x,y,z,color='#f6d7a0'){const c=document.createElement('canvas');c.width=512;c.height=64;const ctx=c.getContext('2d');ctx.fillStyle='#1d140ce0';ctx.fillRect(0,0,512,64);ctx.font='bold 24px sans-serif';ctx.textAlign='center';ctx.fillStyle=color;ctx.fillText(text,256,42);const tex=new T.CanvasTexture(c);tex.colorSpace=T.SRGBColorSpace;const sp=new T.Sprite(new T.SpriteMaterial({map:tex,depthTest:false}));sp.position.set(x,y,z);sp.scale.set(9,1.125,1);scene.add(sp);}
 const floor=box(36,-.3,32,72,.6,64,'#755537');floor.userData.terrain=true;pick.push(floor);
 for(let y=0;y<map.height;y++)for(let x=0;x<map.width;x++)if(x<2||y<2||x>33||y>29){const m=mesh(rockGeo,['#59432b','#705330','#483723'][(x*7+y*3)%3],x*2+1,2.2,y*2+1,1.65,3+(x+y)%3,1.7);m.rotation.y=(x+y)*.7;}
 for(const [x,y] of map.rocks){mesh(rockGeo,'#5e5140',x*2+1,.75,y*2+1,1.25,1.1,1.1);}
 for(let i=0;i<50;i++){const patch=mesh(new T.CircleGeometry(1.1+(i%4)*.5,6),i%2?'#6e5032':'#7e5c39',4+(i*19%63),.007,4+(i*13%53));patch.rotation.x=-Math.PI/2;}
 // Small rubble remains decorative; large rocks above are in the collision grid.
 for(let i=0;i<70;i++){const x=3+(i*17%62),z=4+(i*23%52);mesh(rockGeo,i%2?'#80613b':'#4b3a2a',x,.1,z,.12+(i%3)*.08,.15,.2);}
 const colors={cobre:'#c88043',plata:'#c8d9e1',oro:'#ffc937'};
 for(const d of map.nodes){const g=new T.Group();g.position.set(d.x*2+1,0,d.y*2+1);scene.add(g);const part=(geo,c,x,y,z,sx,sy,sz)=>{const m=new T.Mesh(geo,typeof c==='string'?mat(c):c);m.position.set(x,y,z);m.scale.set(sx,sy,sz);m.userData.id=d.id;g.add(m);pick.push(m);return m;};
  if(d.type==='mineral_rock'){part(rockGeo,'#5f503d',0,.8,0,1.25,1.1,1.1);const veins=[];for(let i=0;i<5;i++){const a=i*1.7;veins.push(part(rockGeo,colors[d.mineral],Math.sin(a)*1.03,1.25+(i%3)*.32,Math.cos(a)*1.03,.38,.2,.3));}resources.set(d.id,{g,veins});label(d.mineral.toUpperCase(),d.x*2+1,3.2,d.y*2+1,colors[d.mineral]);
   if(d.mineral==='oro'&&(d.y===3||d.x===3||d.x===32)){for(let i=0;i<4;i++)part(rockGeo,colors.oro,(i%2)*.7-.3,2+i*.4,-.6,.3,.13,.1);}
  }else if(d.type==='furnace'){
   part(boxGeo,'#4e4034',0,.35,0,3.8,.7,3.4);part(boxGeo,'#80715e',-1.25,1.4,0,.65,2.3,2.8);part(boxGeo,'#80715e',1.25,1.4,0,.65,2.3,2.8);part(boxGeo,'#6c5944',0,2.65,0,3.3,.6,2.8);part(boxGeo,'#29201a',0,1.3,-1.2,2,2,.4);part(boxGeo,'#4f4539',.6,3.6,-.5,.9,1.6,1);
   const fire=new T.MeshBasicMaterial({color:'#ff8b28'});part(rockGeo,fire,0,.8,.3,.9,.4,.75);const light=new T.PointLight(0xff8a36,55,22,2);light.position.set(d.x*2+1,2,d.y*2+2);scene.add(light);resources.set(d.id,{fire,light});label('HORNO · FUNDIR / ACUÑAR',d.x*2+1,5.5,d.y*2+1);
  }else {part(rockGeo,'#6f4f2c',0,2,0,2.4,2.7,1);part(boxGeo,'#130e0b',0,1.5,1.05,2.5,2.8,.15);label('SALIDA A LAS PALMAS',d.x*2+1,5,d.y*2+1);}
 }
 for(const [x,z] of [[8,10],[60,10],[8,48],[60,48],[35,8],[35,52]]){box(x,1.6,z,.14,3.2,.14,'#33271b');mesh(new T.SphereGeometry(.22,8,6),new T.MeshBasicMaterial({color:'#ffe4a0'}),x,3.3,z);const light=new T.PointLight(0xffcc83,38,24,2);light.position.set(x,3,z);scene.add(light);}
 // Timber supports and a wooden mine cart echo the supplied low-poly references.
 for(const x of [9,61]){box(x,2.3,27,.6,4.6,.6,'#3d291b');box(x,4.6,27,5,.5,.6,'#67472b');}
 box(22,.7,37,2.2,1.1,1.5,'#493b2e');for(const x of [21.2,22.8])for(const z of [36.3,37.7])mesh(new T.CylinderGeometry(.3,.3,.15,8),'#282626',x,.25,z).rotation.x=Math.PI/2;
 return {scene,pick,update(state,time){for(const [id,r] of resources){if(r.veins){const active=state.nodes.get(id)?.state==='active';for(const v of r.veins)v.visible=active;r.g.scale.y=active?1:.48;}if(r.light){r.light.intensity=(time<state.forgeUntil?75:48)+Math.sin(time*.012)*4;r.fire.color.set(time<state.forgeUntil?'#ffd25b':'#ff8b28');}}}};
}
