/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Shared, deterministic inventory and furnace rules. */
(function(root){
 const recipes={mineral_cobre:{metal:'cobre',name:'Cobre',ore:3,coins:4,xp:9},mineral_plata:{metal:'plata',name:'Plata',ore:4,coins:12,xp:15},mineral_oro:{metal:'oro',name:'Oro',ore:5,coins:30,xp:24},pepita_oro:{metal:'oro',name:'Oro fluvial',ore:5,coins:30,xp:24}};
 function count(inv,id){return inv.reduce((sum,s)=>sum+(s?.item===id?s.qty:0),0);}
 function add(inv,items,id,qty,slots){if(!items[id]||!Number.isSafeInteger(qty)||qty<=0)return null;const next=inv.map(s=>s?{...s}:null),it=items[id],max=it.stackable?(it.maxStack||999):1;let left=qty;
  for(const s of next)if(s?.item===id&&s.qty<max){const n=Math.min(left,max-s.qty);s.qty+=n;left-=n;if(!left)return next;}
  for(let i=0;i<slots&&left;i++)if(!next[i]){const n=Math.min(left,max);next[i]={item:id,qty:n};left-=n;}return left?null:next;
 }
 function remove(inv,id,qty){if(!Number.isSafeInteger(qty)||qty<=0||count(inv,id)<qty)return null;const next=inv.map(s=>s?{...s}:null);for(let i=0;i<next.length&&qty;i++)if(next[i]?.item===id){const n=Math.min(qty,next[i].qty);next[i].qty-=n;qty-=n;if(!next[i].qty)next[i]=null;}return next;}
 function smelt(inv,items,id,batches,mode,slots){const r=recipes[id];if(!r||!Number.isSafeInteger(batches)||batches<1||!['ingot','coins'].includes(mode))return {error:'Elige una cantidad válida.'};const cost=r.ore*batches;let next=remove(inv,id,cost);if(!next)return {error:`Necesitas ${cost} unidades de ${r.name.toLowerCase()}.`};if(mode==='ingot'){next=add(next,items,'lingote_'+r.metal,batches,slots);if(!next)return {error:'No hay espacio para los lingotes. Libera una casilla.'};}return {inv:next,coins:mode==='coins'?r.coins*batches:0,qty:batches,cost,xp:r.xp*batches};}
 root.MiningRules={recipes,count,add,remove,smelt};
})(typeof window==='undefined'?globalThis:window);
