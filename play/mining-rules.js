/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Shared, deterministic inventory and furnace rules.
   Acuñar monedas crea objetos de mochila (moneda_*). No emite SMC.
   El modo "coins" sólo calcula el monto: quien acredita SMC es el libro mayor. */
(function(root){
 const recipes={
  mineral_cobre:{metal:'cobre',name:'Cobre',ore:3,ingots:1,coinItem:'moneda_cobre',coinQty:4,coins:4,xp:9},
  mineral_plata:{metal:'plata',name:'Plata',ore:4,ingots:1,coinItem:'moneda_plata',coinQty:3,coins:12,xp:15},
  mineral_oro:{metal:'oro',name:'Oro',ore:5,ingots:1,coinItem:'moneda_oro',coinQty:2,coins:30,xp:24},
  pepita_oro:{metal:'oro',name:'Oro fluvial',ore:5,ingots:1,coinItem:'moneda_oro',coinQty:2,coins:30,xp:24}
 };
 function count(inv,id){return inv.reduce((sum,s)=>sum+(s?.item===id?s.qty:0),0);}
 function add(inv,items,id,qty,slots){if(!items[id]||!Number.isSafeInteger(qty)||qty<=0)return null;const next=inv.map(s=>s?{...s}:null),it=items[id],max=it.stackable?(it.maxStack||999):1;let left=qty;
  for(const s of next)if(s?.item===id&&s.qty<max){const n=Math.min(left,max-s.qty);s.qty+=n;left-=n;if(!left)return next;}
  for(let i=0;i<slots&&left;i++)if(!next[i]){const n=Math.min(left,max);next[i]={item:id,qty:n};left-=n;}return left?null:next;
 }
 function remove(inv,id,qty){if(!Number.isSafeInteger(qty)||qty<=0||count(inv,id)<qty)return null;const next=inv.map(s=>s?{...s}:null);for(let i=0;i<next.length&&qty;i++)if(next[i]?.item===id){const n=Math.min(qty,next[i].qty);next[i].qty-=n;qty-=n;if(!next[i].qty)next[i]=null;}return next;}
 function smelt(inv,items,id,batches,mode,slots){
  const r=recipes[id];
  if(!r||!Number.isSafeInteger(batches)||batches<1||!['ingot','coin','coins'].includes(mode))return {error:'Elige una cantidad válida.'};
  const cost=r.ore*batches;
  let next=remove(inv,id,cost);
  if(!next)return {error:'Necesitas '+cost+' unidades de '+r.name.toLowerCase()+'.'};
  if(mode==='ingot'){
   const qty=(r.ingots||1)*batches;
   next=add(next,items,'lingote_'+r.metal,qty,slots);
   if(!next)return {error:'No hay espacio para los lingotes. Libera una casilla.'};
   return {inv:next,coins:0,item:'lingote_'+r.metal,qty:qty,cost:cost,xp:r.xp*batches};
  }
  if(mode==='coin'){
   const qty=r.coinQty*batches;
   next=add(next,items,r.coinItem,qty,slots);
   if(!next)return {error:'No hay espacio para las monedas. Libera una casilla.'};
   return {inv:next,coins:0,item:r.coinItem,qty:qty,cost:cost,xp:r.xp*batches};
  }
  return {inv:next,coins:r.coins*batches,qty:batches,cost:cost,xp:r.xp*batches};
 }
 root.MiningRules={recipes,count,add,remove,smelt};
})(typeof window==='undefined'?globalThis:window);
