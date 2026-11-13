/* SPDX-License-Identifier: AGPL-3.0-or-later */
(() => {
 const panel=document.querySelector('#hud-chat'), toggle=document.querySelector('#chat-toggle'), count=document.querySelector('#chat-count');
 let unread=0;
 function badge(){count.hidden=!unread;count.textContent=unread>99?'99+':String(unread);toggle.setAttribute('aria-label',unread?`Abrir chat, ${unread} mensajes nuevos`:'Abrir chat');}
 window.ChatUI={setOpen(open,focus=false){panel.hidden=!open;toggle.setAttribute('aria-expanded',String(open));if(open){unread=0;badge();const log=document.querySelector('#chat-log');log.scrollTop=log.scrollHeight;if(focus)document.querySelector('#chat-input').focus();}else{document.querySelector('#chat-input').blur();toggle.focus({preventScroll:true});}},received(channel){if(panel.hidden&& !['sys','juego'].includes(channel)){unread++;badge();}}};
 toggle.onclick=()=>window.ChatUI.setOpen(panel.hidden);
 const clean=document.querySelector('#hud-toggle');
 clean.onclick=()=>{const on=document.body.classList.toggle('solo-mundo');clean.textContent=on?'Mostrar interfaz':'Solo mundo';clean.setAttribute('aria-pressed',String(on));if(on)window.ChatUI.setOpen(false);clean.focus({preventScroll:true});};
 const restore=document.createElement('button');restore.id='info-restore';restore.className='hud';restore.textContent='Mostrar avisos';restore.hidden=true;document.body.append(restore);restore.onclick=()=>{document.querySelectorAll('.info-dismissed').forEach(el=>el.classList.remove('info-dismissed'));restore.hidden=true;};
 for(const id of ['objetivo','aviso','dialogo']){const el=document.getElementById(id),b=document.createElement('button');b.type='button';b.className='info-fold';b.textContent='−';b.setAttribute('aria-label','Minimizar información');b.onclick=e=>{e.stopPropagation();const min=el.classList.toggle('info-min');b.textContent=min?'Información +':'−';b.setAttribute('aria-label',min?'Mostrar información':'Minimizar información');};el.prepend(b);const x=document.createElement('button');x.type='button';x.className='info-close';x.textContent='×';x.setAttribute('aria-label','Cerrar mensaje emergente');x.onclick=e=>{e.stopPropagation();el.classList.add('info-dismissed');restore.hidden=false;};el.prepend(x);}
 // Keep the composer above the software keyboard without resizing the 3D world.
 function viewport(){const v=window.visualViewport;document.documentElement.style.setProperty('--keyboard',Math.max(0,innerHeight-(v?v.height+v.offsetTop:innerHeight))+'px');}
 window.visualViewport?.addEventListener('resize',viewport);window.visualViewport?.addEventListener('scroll',viewport);viewport();
})();
