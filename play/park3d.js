/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Mesh scenery follows world data so parks and waterways move with the map.
export function enrichWorld(T,scene,W,pick,height,material){
 const mesh=(geo,c,x,y,z)=>{const m=new T.Mesh(geo,typeof c==='string'?material(c):c);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;scene.add(m);return m;};
 const box=(x,y,z,w,h,d,c)=>mesh(new T.BoxGeometry(w,h,d),c,x,y,z);
 const disc=(x,y,z,r,h,c)=>mesh(new T.CylinderGeometry(r,r,h,48),c,x,y,z);
 const ground=(x,z)=>height(x/2,z/2);
 const paving=document.createElement('canvas');paving.width=paving.height=256;const ctx=paving.getContext('2d');ctx.fillStyle='#ab8068';ctx.fillRect(0,0,256,256);for(let row=0;row<8;row++)for(let col=-1;col<5;col++){const v=(row*17+col*23+91)%16;ctx.fillStyle=`rgb(${177+v},${119+v},${88+v})`;ctx.fillRect(col*64+(row%2)*32+1,row*32+1,62,30);}const texture=new T.CanvasTexture(paving);texture.colorSpace=T.SRGBColorSpace;texture.wrapS=texture.wrapT=T.RepeatWrapping;texture.anisotropy=4;const pavement=material('#bd886d');pavement.color.set('#ffffff');pavement.map=texture;pavement.needsUpdate=true;

 // Large neutral concrete slabs, fine joints and subtle tonal variation.
 const greyCanvas=document.createElement('canvas');greyCanvas.width=greyCanvas.height=256;const grey=greyCanvas.getContext('2d');grey.fillStyle='#91999b';grey.fillRect(0,0,256,256);
 for(let row=0;row<4;row++)for(let col=0;col<2;col++){const value=173+((row*3+col*5)%4)*3;grey.fillStyle=`rgb(${value-4},${value},${value+1})`;grey.fillRect(col*128+1,row*64+1,126,62);grey.strokeStyle='#c3c8c9';grey.lineWidth=1;grey.strokeRect(col*128+2,row*64+2,124,60);}
 const greyTexture=new T.CanvasTexture(greyCanvas);greyTexture.colorSpace=T.SRGBColorSpace;greyTexture.wrapS=greyTexture.wrapT=T.RepeatWrapping;greyTexture.anisotropy=4;const modernPaving=material('#aab0b1');modernPaving.color.set('#ffffff');modernPaving.map=greyTexture;modernPaving.needsUpdate=true;
 function tree(x,z,palm=false){const y=ground(x,z);mesh(new T.CylinderGeometry(.14,.25,palm?6.4:3.6,8),'#89745a',x,y+(palm?3.2:1.8),z);if(palm){for(let i=0;i<9;i++){const a=i*Math.PI*2/9;const m=mesh(new T.SphereGeometry(1,8,4),'#597c4c',x+Math.cos(a)*1.3,y+6.3,z+Math.sin(a)*1.3);m.scale.set(2.2,.13,.5);m.rotation.y=-a;}}else for(let i=0;i<5;i++){const a=i*2.4;const m=mesh(new T.IcosahedronGeometry(1,1),['#53774a','#67864f','#3e6549'][i%3],x+Math.cos(a),y+4.2+(i%2)*.5,z+Math.sin(a));m.scale.set(1.7,1.2,1.7);}}
 function bench(){ /* Las bancas de listón las reemplaza la banca de concreto instanciada. */ }
 const lamps=[], positions=new Set();
 const glowCanvas=document.createElement('canvas');glowCanvas.width=glowCanvas.height=64;const glowCtx=glowCanvas.getContext('2d');const gradient=glowCtx.createRadialGradient(32,32,0,32,32,32);gradient.addColorStop(0,'rgba(255,218,112,.65)');gradient.addColorStop(.4,'rgba(255,186,65,.25)');gradient.addColorStop(1,'rgba(255,186,65,0)');glowCtx.fillStyle=gradient;glowCtx.fillRect(0,0,64,64);const glowTexture=new T.CanvasTexture(glowCanvas);
 const bulbMaterial=new T.MeshBasicMaterial({color:'#ffe8a0'});
 function lamp(x,z){if(lamps.some(l=>Math.hypot(l.x-x,l.z-z)<4))return;const y=ground(x,z);const key=`${Math.round(x)},${Math.round(z)}`;if(positions.has(key))return;positions.add(key);
  disc(x,y+.12,z,.4,.24,'#272c29');disc(x,y+.36,z,.25,.3,'#30352d');mesh(new T.CylinderGeometry(.08,.15,4,8),'#272c29',x,y+2.3,z);
  for(const side of [-1,1]){const arm=box(x+side*.5,y+4.2,z,1.25,.12,.12,'#272c29');arm.rotation.z=side*.5;const lx=x+side*1.05;
   box(lx,y+4.3,z,.42,.7,.42,bulbMaterial);mesh(new T.ConeGeometry(.43,.35,4),'#242a26',lx,y+4.83,z);mesh(new T.ConeGeometry(.3,.3,4),'#242a26',lx,y+3.8,z);
   for(const dx of [-.23,.23])for(const dz of [-.23,.23])box(lx+dx,y+4.3,z+dz,.045,.8,.045,'#272c29');
  }
  const glow=new T.Mesh(new T.PlaneGeometry(13,13),new T.MeshBasicMaterial({map:glowTexture,transparent:true,depthWrite:false,blending:T.AdditiveBlending}));glow.rotation.x=-Math.PI/2;glow.position.set(x,y+.12,z);scene.add(glow);lamps.push({x,z,y,glow});
 }
 function planter(x,z,palm=false){const y=ground(x,z);disc(x,y+.18,z,1.6,.36,'#aaa38e');disc(x,y+.39,z,1.4,.08,'#5d754f');tree(x,z,palm);}
 for(const park of W.parkDetails||[]){const cx=park.x*2,cz=park.y*2,cy=ground(cx,cz);
  if(park.id==='poblado'){
   disc(cx,cy-.05,cz,8.8,.18,'#bca98c');for(let i=3;i>=0;i--){const radius=5+i*1.05;const ring=mesh(new T.RingGeometry(radius-.65,radius,80),i%2?'#c49276':'#b47c61',cx,cy+.025+i*.025,cz);ring.rotation.x=-Math.PI/2;const rim=mesh(new T.TorusGeometry(radius,.09,6,80),'#b7a18c',cx,cy+.08+i*.025,cz);rim.rotation.x=Math.PI/2;}disc(cx,cy+.06,cz,4.1,.12,'#c99172');
   for(const [dx,dz] of [[-6,-11],[8,-8],[-9,4],[7,9]])planter(cx+dx,cz+dz);
   for(const [dx,dz] of [[-8,-7],[9,1],[-5,10],[14,9],[7,2]])bench(cx+dx,cz+dz,.4);
   for(const [dx,dz] of [[-10,-14],[3,-13],[-8,12],[10,12],[12,-11]])tree(cx+dx,cz+dz,true);
   for(const [dx,dz] of [[-12,-14],[-6,10],[11,-3],[16,5]])lamp(cx+dx,cz+dz);
  }else{
   // An open, shaded formal square leaves the central walking axis clear.
   const spread=park.id==='envigado'?16:park.id==='sabaneta'?22:10;
   for(const dx of [-spread,spread])for(const dz of [-8,8]){planter(cx+dx,cz+dz,true);bench(cx+dx+(dx<0?3:-3),cz+dz,dx<0?Math.PI/2:-Math.PI/2);lamp(cx+dx,cz+dz+3);}
   if(park.id==='sabaneta'){box(cx,cy+.65,cz+5,1.7,1.3,1.7,'#b3ae9b');box(cx,cy+1.9,cz+5,.65,1.2,.4,'#595f4f');mesh(new T.SphereGeometry(.3,10,8),'#595f4f',cx,cy+2.7,cz+5);for(const dx of [-14,14])for(const dz of [-13,12])bench(cx+dx,cz+dz,dx<0?Math.PI/2:-Math.PI/2);}
   if(park.id==='envigado'){disc(cx,cy+.3,cz+6,2.2,.6,'#bfb8a6');disc(cx,cy+.64,cz+6,1.9,.07,'#78b3ba');disc(cx,cy+1.2,cz+6,.22,1.1,'#d7d0bc');}
   if(park.id==='la_estrella'){for(let i=0;i<5;i++){const a=-Math.PI/2+i*Math.PI*2/5;tree(cx+Math.cos(a)*5.5,cz+Math.sin(a)*5.5);}}
  }
 }
 const bridges=W.bridges||[];
 const isCrossing=(x,y)=>bridges.some(b=>x>=b.x-1&&x<b.x+b.w+1&&y>=b.y-1&&y<b.y+b.h+1);
 for(const r of W.riverLayouts||[]){
  if(r.axis==='y')for(let y=r.y;y<r.y+r.h;y++){if(isCrossing(r.x,y)||W.riverLayouts.some(q=>q.axis==='x'&&y>=q.y&&y<q.y+q.h))continue;for(const x of [r.x*2-.2,(r.x+r.w)*2+.2])box(x,r.id==='rio_claro'?.12:.28,y*2+1,.25,r.id==='rio_claro'?.28:.5,2,'#a6a794');if(y%3===0)box(r.x*2+.8,(r.waterLevel??-.45)+.04,y*2+1,.75,.015,.04,'#a8c5c5');}
  else for(let x=r.x;x<r.x+r.w;x++){if(isCrossing(x,r.y)||W.riverLayouts.some(q=>q.axis==='y'&&x>=q.x&&x<q.x+q.w))continue;for(const z of [r.y*2-.2,(r.y+r.h)*2+.2])box(x*2+1,.28,z,2,.5,.32,'#a6a794');if(x%3===0)box(x*2+1,-.41,r.y*2+3+(x%3),1.5,.015,.06,'#91c7c8');}
 }
 for(const b of bridges){if(b.axis==='x'){for(const z of [b.y*2-.15,(b.y+b.h)*2+.15]){box((b.x+b.w/2)*2,1,z,b.w*2,.13,.13,'#5c6c66');for(let x=b.x*2;x<=(b.x+b.w)*2;x+=2)box(x,.65,z,.12,1.2,.12,'#5c6c66');}}else for(const x of [b.x*2-.15,(b.x+b.w)*2+.15]){box(x,1,(b.y+b.h/2)*2,.13,.13,b.h*2,'#5c6c66');for(let z=b.y*2;z<=(b.y+b.h)*2;z+=2)box(x,.65,z,.12,1.2,.12,'#5c6c66');}}
 for(const d of W.scenery3d||[])if(d.kind==='tree')tree(d.x*2+1,d.y*2+1);else lamp(d.x*2+1,d.y*2+1);
 for(const d of W.signs3d||[]){const c=document.createElement('canvas');c.width=640;c.height=96;const ctx=c.getContext('2d');ctx.fillStyle='#354b45';ctx.fillRect(0,0,640,96);ctx.strokeStyle='#c4b081';ctx.lineWidth=5;ctx.strokeRect(4,4,632,88);ctx.fillStyle='#f0e7cf';ctx.font='bold 28px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(d.text,320,48,615);const tex=new T.CanvasTexture(c);tex.colorSpace=T.SRGBColorSpace;const m=new T.Mesh(new T.BoxGeometry(5.8,.9,.12),[material('#354b45'),material('#354b45'),material('#354b45'),material('#354b45'),new T.MeshBasicMaterial({map:tex}),material('#354b45')]);m.position.set(d.x*2+1,height(d.x,d.y)+2.8,d.y*2+1);scene.add(m);box(d.x*2+1,height(d.x,d.y)+1.3,d.y*2+1,.12,2.6,.12,'#354b45');}
 // Repeat lamps along walkable streets and paths, keeping water and buildings clear.
 if(!W.valle?.chunked)for(let y=2;y<W.height-2;y+=6)for(let x=2;x<W.width-2;x+=6){const kind=W.tiles[W.ground[y][x]].kind;if(!W.collision[y][x]&&['path','cobble','pavement','asphalt','bridge'].includes(kind))lamp(x*2+1,y*2+1);}
 const nearbyLights=Array.from({length:8},()=>{const light=new T.PointLight(0xffd077,0,18,2);scene.add(light);return light;});
 return {count:lamps.length,update(night,player){const closest=night?[...lamps].sort((a,b)=>Math.hypot(a.x-player.x,a.z-player.z)-Math.hypot(b.x-player.x,b.z-player.z)).slice(0,8):[];for(const l of lamps)l.glow.visible=night;for(let i=0;i<nearbyLights.length;i++){const l=closest[i],light=nearbyLights[i];light.intensity=l?28:0;if(l)light.position.set(l.x,l.y+4.1,l.z);}}};

}
