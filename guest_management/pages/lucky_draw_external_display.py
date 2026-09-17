"""EventLah Lucky Draw external hall display.

Presentation-only browser window. The operator page remains authoritative;
this page mirrors its BroadcastChannel/localStorage payload.
"""

import reflex as rx


def lucky_draw_external_display_page():
    """Fullscreen audience display synchronized with the operator draw."""
    html = r'''<!doctype html>
<html><head><style>
html,body,#__next{margin:0!important;padding:0!important;width:100%!important;height:100%!important;overflow:hidden!important;background:#050505!important;color:#fff!important}
*{box-sizing:border-box}
#ext-screen{width:100vw;height:100vh;display:grid;grid-template-rows:54px minmax(0,1fr) 82px;overflow:hidden;background:#050505;color:#fff;font-family:Inter,Arial,sans-serif}
#ext-header{display:flex;align-items:center;justify-content:center;border-bottom:1px solid rgba(212,175,55,.35);min-height:0}
#ext-event{color:#D4AF37;font-size:clamp(18px,2vw,30px);font-weight:900;letter-spacing:.08em;text-transform:uppercase}
#ext-main{min-height:0;display:grid;grid-template-columns:minmax(0,.82fr) minmax(0,1.18fr);gap:10px;padding:10px;overflow:hidden}
.ext-panel{min-width:0;min-height:0;overflow:hidden;border:1px solid rgba(212,175,55,.45);border-radius:16px;background:#151515;display:flex;align-items:center;justify-content:center}
#ext-prize-panel{padding:10px}#ext-prize-inner{width:100%;height:100%;min-height:0;display:grid;grid-template-rows:auto auto minmax(0,1fr);align-items:center;justify-items:center;gap:8px}
.ext-label{color:#D4AF37;font-size:clamp(9px,.8vw,13px);font-weight:900;letter-spacing:.16em;text-transform:uppercase}
#ext-prize{color:#fff;font-size:clamp(22px,2.7vw,42px);font-weight:900;line-height:1;text-align:center}#ext-value{color:#D4AF37;font-size:clamp(16px,1.7vw,28px);font-weight:900;text-align:center;margin-top:4px}
#ext-prize-media{width:min(100%,430px);height:min(100%,38vh);min-height:0;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden;border:1px solid rgba(212,175,55,.35);border-radius:12px;background:#080808}
#ext-prize-image{width:100%;height:100%;display:none;object-fit:contain;object-position:center}#ext-prize-placeholder{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#D4AF37;font-size:60px}#ext-prize-error{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);color:#aaa;font-size:10px;white-space:nowrap;display:none}
#ext-result-panel{padding:8px}#ext-result-inner{width:100%;height:100%;min-height:0;display:flex;align-items:center;justify-content:center;overflow:hidden}#ext-result-inner>.ext-card{max-height:90%;}
#ext-wheel-stage{width:100%;height:100%;min-height:0;display:flex;align-items:center;justify-content:center}.ext-hidden{display:none!important}#ext-wheel-stage.ext-hidden{display:none!important}
#ext-wheel-wrap{position:relative;width:min(38vh,380px);height:min(38vh,380px);flex:0 0 auto;display:flex;align-items:center;justify-content:center}
#ext-wheel{position:relative;width:100%;height:100%;border-radius:50%;background:conic-gradient(from 0deg,rgba(212,175,55,.20),rgba(212,175,55,.40),rgba(212,175,55,.60),rgba(212,175,55,.80),rgba(212,175,55,.60),rgba(212,175,55,.40),rgba(212,175,55,.20));border:8px solid #D4AF37;box-shadow:0 0 40px #D4AF37,inset 0 0 20px #D4AF37;backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;overflow:visible}
#ext-wheel:before{content:'';position:absolute;top:-27px;left:50%;transform:translateX(-50%);z-index:5;border-left:18px solid transparent;border-right:18px solid transparent;border-top:32px solid #D4AF37;filter:drop-shadow(0 0 7px rgba(212,175,55,.75))}

#ext-center{position:absolute;z-index:3;width:46%;height:46%;border-radius:50%;background:#171717;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:5%;box-shadow:0 0 22px rgba(212,175,55,.18);overflow:hidden}
#ext-wheel-name{width:88%;color:#D4AF37;font-size:clamp(17px,2.2vw,34px);font-weight:900;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:0 0 12px rgba(212,175,55,.7)}#ext-wheel-id{color:#bbb;font-size:clamp(9px,.8vw,14px);margin-top:3px}
.ext-spinning{animation:wheelSpin .08s linear infinite}@keyframes wheelSpin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
.ext-card{width:min(90%,700px);max-height:88%;overflow:hidden;padding:clamp(18px,3vh,32px) clamp(18px,3vw,44px);border:1px solid #D4AF37;border-radius:18px;background:#101010;text-align:center;display:none;flex-direction:column;align-items:center;justify-content:center}
#ext-candidate-name,#ext-winner-name{color:#fff;font-size:clamp(26px,4vw,60px);font-weight:900;line-height:1.05;margin:8px 0;text-shadow:0 0 18px rgba(212,175,55,.75)}.ext-id{color:#bbb;font-size:clamp(11px,1.1vw,18px)}.ext-card-prize{color:#D4AF37;font-size:clamp(15px,1.6vw,25px);font-weight:900;margin-top:7px}.ext-confirmed{color:#D4AF37;font-size:clamp(12px,1.2vw,20px);font-weight:900;margin-top:9px}
#ext-ready-card{display:flex}#ext-ready-icon{color:#D4AF37;font-size:clamp(40px,5vw,70px);line-height:1}#ext-ready-title{color:#fff;font-size:clamp(17px,1.9vw,28px);font-weight:900;margin-top:6px}#ext-ready-subtitle{color:#aaa;font-size:clamp(11px,1.1vw,17px)}
#ext-footer{min-height:0;border-top:1px solid rgba(212,175,55,.25);padding:5px 12px;display:grid;grid-template-rows:17px minmax(0,1fr);overflow:hidden}#ext-progress-row{display:flex;align-items:center;justify-content:space-between;color:#aaa;font-size:10px}#ext-progress-label{color:#D4AF37;font-weight:900;letter-spacing:.14em}
#ext-history{min-height:0;overflow-y:auto;overflow-x:hidden;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px 16px}.ext-history-row{min-width:0;display:flex;justify-content:space-between;gap:7px;padding:1px 0;border-bottom:1px solid #222;color:#ddd;font-size:9px}.ext-history-row span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ext-history-row span:last-child{color:#D4AF37}
@media(max-width:900px){#ext-screen{grid-template-rows:50px minmax(0,1fr) 58px}#ext-main{gap:6px;padding:6px}#ext-prize-panel,#ext-result-panel{padding:6px}#ext-wheel-wrap{width:min(32vh,300px);height:min(32vh,300px)}#ext-history{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){#ext-main{grid-template-columns:1fr 1fr}#ext-wheel-wrap{width:min(28vh,240px);height:min(28vh,240px)}#ext-prize{font-size:clamp(18px,4vw,28px)}#ext-value{font-size:clamp(14px,3vw,22px)}}
</style></head><body>
<div id="ext-screen">
<header id="ext-header"><div id="ext-event">Lucky Draw</div></header>
<main id="ext-main">
<section id="ext-prize-panel" class="ext-panel"><div id="ext-prize-inner"><div class="ext-label">CURRENT PRIZE</div><div><div id="ext-prize">Prize</div><div id="ext-value"></div></div><div id="ext-prize-media"><img id="ext-prize-image" alt="Prize image"><div id="ext-prize-placeholder">✦</div><div id="ext-prize-error">Prize image could not be loaded</div></div></div></section>
<section id="ext-result-panel" class="ext-panel"><div id="ext-result-inner">
<div id="ext-wheel-stage"><div id="ext-wheel-wrap"><div id="ext-wheel">
<div id="ext-center"><div id="ext-wheel-name">Ready...</div><div id="ext-wheel-id"></div></div>
</div></div></div>
<div id="ext-candidate-card" class="ext-card"><div class="ext-label">CANDIDATE</div><div id="ext-candidate-name"></div><div id="ext-candidate-id" class="ext-id"></div><div id="ext-candidate-prize" class="ext-card-prize"></div><div class="ext-confirmed">AWAITING PRESENT / ABSENT DECISION</div></div>
<div id="ext-winner-card" class="ext-card"><div class="ext-label">WINNER!</div><div id="ext-winner-name"></div><div id="ext-winner-id" class="ext-id"></div><div id="ext-winner-prize" class="ext-card-prize"></div><div class="ext-confirmed">WINNER CONFIRMED</div></div>
<div id="ext-ready-card" class="ext-card"><div id="ext-ready-icon">✦</div><div id="ext-ready-title">Ready to Draw!</div><div id="ext-ready-subtitle">The next prize is ready.</div></div>
</div></section></main>
<footer id="ext-footer"><div id="ext-progress-row"><span id="ext-progress-label">PRIZE PROGRESS</span><span id="ext-progress">0 / 0</span></div><div id="ext-history"></div></footer>
</div>
<script>
(() => {
 const channelName='eventlah-lucky-draw', storageKey='eventlah-lucky-draw-state';
 const parts=window.location.pathname.split('/').filter(Boolean); const expectedEvent=decodeURIComponent(parts[parts.length-1]||'');
 const $=id=>document.getElementById(id); const text=(id,v)=>{const e=$(id);if(e)e.textContent=v==null?'':String(v)};
 const show=(id,yes)=>{const e=$(id);if(e)e.classList.toggle('ext-hidden',!yes)};
 let spinning=false,lastImage='',lastPayloadSignature='';
 function slots(){}
 function image(url){const im=$('ext-prize-image'),ph=$('ext-prize-placeholder'),er=$('ext-prize-error');if(!im)return;if(!url){im.removeAttribute('src');im.style.display='none';ph.style.display='flex';er.style.display='none';lastImage='';return}if(url===lastImage&&im.complete&&im.naturalWidth){im.style.display='block';ph.style.display='none';er.style.display='none';return}lastImage=url;er.style.display='none';im.onload=()=>{im.style.display='block';ph.style.display='none';er.style.display='none'};im.onerror=()=>{im.style.display='none';ph.style.display='flex';er.style.display='block'};im.src=url}
 function render(s){
 if(!s)return;
 if(String(s.event_id||'')!==expectedEvent)return;
 const signature=JSON.stringify(s);
 if(signature===lastPayloadSignature)return;
 lastPayloadSignature=signature;
 text('ext-event',s.event_name||'Lucky Draw');text('ext-prize',s.prize_name||'Prize');text('ext-value',s.prize_value||'');text('ext-progress',`${Number(s.prize_index||0)+1} / ${Number(s.prize_count||0)}`);image(String(s.prize_picture||''));
 const names=Array.isArray(s.wheel_names)?s.wheel_names:[];document.querySelectorAll('.ext-slot').forEach((e,i)=>e.textContent=names.length?(names[i%names.length]||'Guest'):'');
 text('ext-wheel-name',s.current_name||'Ready...');text('ext-wheel-id',s.current_id?`ID: ${s.current_id}`:'');text('ext-candidate-name',s.current_name||'');text('ext-candidate-id',s.current_id?`ID: ${s.current_id}`:'');text('ext-candidate-prize',s.prize_name||'');text('ext-winner-name',s.current_name||'');text('ext-winner-id',s.current_id?`ID: ${s.current_id}`:'');text('ext-winner-prize',s.prize_name||'');
 const status=String(s.status||'READY'), draw=Boolean(s.spinning)&&status==='DRAWING', cand=status==='CANDIDATE', conf=status==='CONFIRMED'; const w=$('ext-wheel');if(w){if(draw&&!spinning){w.classList.add('ext-spinning');spinning=true}if(!draw&&spinning){w.classList.remove('ext-spinning');spinning=false}}
 show('ext-wheel-stage',draw||cand);show('ext-candidate-card',cand);show('ext-winner-card',conf);show('ext-ready-card',!draw&&!cand&&!conf);
 const h=$('ext-history');if(h&&Array.isArray(s.winners)){const sig=JSON.stringify(s.winners.slice(0,10));if(h.dataset.sig!==sig){h.dataset.sig=sig;h.replaceChildren();s.winners.slice(0,10).forEach((x,i)=>{const row=document.createElement('div');row.className='ext-history-row';const a=document.createElement('span');a.textContent=`${i+1}. ${x.name||'Winner'}`;const b=document.createElement('span');b.textContent=x.prize_name||x.prize||'';row.append(a,b);h.append(row)})}}
 }
 function load(){
   try{
     const v=localStorage.getItem(storageKey);
     if(v)render(JSON.parse(v));
   }catch(e){}
 }
 function acceptState(s){
   if(!s || String(s.event_id||'')!==expectedEvent)return;
   try{localStorage.setItem(storageKey,JSON.stringify(s));}catch(e){}
   render(s);
 }
 function boot(){
   slots();
   const loaded=loadUrlState();
   if(!loaded)load();
   [250,1000,2500].forEach(ms=>setTimeout(load,ms));
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
 window.addEventListener('resize',slots);
 window.addEventListener('storage',e=>{
   if(e.key===storageKey&&e.newValue){
     try{render(JSON.parse(e.newValue))}catch(_){}
   }
 });
 window.addEventListener('eventlah-lucky-draw-update',e=>acceptState(e.detail));
 setInterval(load,1500);
 try{
   const c=new BroadcastChannel(channelName);
   c.onmessage=e=>acceptState(e.data);
   window.addEventListener('beforeunload',()=>c.close(),{once:true});
 }catch(e){}
})();
</script></body></html>'''
    return rx.html(html)
