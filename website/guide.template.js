
const protocol=__PROTOCOL__;
const setup=document.querySelector('#setup');
const q=s=>document.querySelector(s);
const qa=s=>[...document.querySelectorAll(s)];
let opener=null;
let provider='ChatGPT';
const visitModes={
 wander:{title:'Room to wander.',description:'Follow what catches your eye, with Giorgio there for context, connections, and conversation. No fixed route to finish and no need to see everything.',request:'Wandering: follow my curiosity without imposing a fixed itinerary.'},
 highlights:{title:'A few highlights.',description:'Find a manageable selection of worthwhile works, shaped around your interests and the time you have. Leave room to stop when something catches your eye.',request:'Highlights: help select a few worthwhile works around my interests and time, rather than a comprehensive tour.'},
 tour:{title:'A visit with a little direction.',description:'Build a flexible itinerary with a beginning, a route through the museum, and time to linger. Let Giorgio help connect the stops into a visit that makes sense.',request:'A tour: help build a coherent, walkable itinerary with connected stops, realistic time to linger, and a flexible order.'},
 theme:{title:'Follow a thread.',description:'Build a tour around a subject, movement, or idea you love. From mythology to modern sculpture, let your interests connect the works along the way.',request:'A themed tour: help build a coherent itinerary around my chosen theme, or help me choose a theme if I have not supplied one.'}
};
function visitSettings(){
 if(q('#off-visit-config')){
  const mode=q('[data-visit-mode][aria-pressed=true]').dataset.visitMode;
  const museum=q('#visit-museum').value.trim();
  const interests=q('#visit-interests').value.trim();
  return `For this visit: ${visitModes[mode].request} I have about ${q('#visit-minutes').value} minutes. ${museum?'Museum supplied by me: '+JSON.stringify(museum)+'.':'Ask which museum I am visiting.'} ${interests?(mode==='theme'?'My chosen theme: ':'My interests: ')+JSON.stringify(interests)+'.':'Help me decide what interests me, without assuming a preference.'} Keep the conversation brief, voice-friendly, and flexible so I can look at the art, not my phone. Use available evidence for suggested stops; do not assume current display status or gallery locations. If routing is uncertain, ask for the museum map or on-site signs.`;
 }
 if(!q('#visit-config'))return '';
 const pace=q('[name=pace]:checked').value;
 const minutes=q('[name=time]:checked').value;
 return `For this visit: ${pace}. I have about ${minutes} minutes. Keep it conversational, brief, and flexible. Ask which museum I am in; do not assume my location or what is on view.`;
}
function textToCopy(){return protocol+(visitSettings()?'\n\n## My visit preferences\n'+visitSettings():'');}
function showSetup(event){opener=event.currentTarget;q('#guide-text').value=textToCopy();q('#chosen-visit').textContent=[q('[data-visit-mode][aria-pressed=true]').textContent,q('#visit-minutes').selectedOptions[0].textContent,q('#visit-museum').value.trim(),q('#visit-interests').value.trim()].filter(Boolean).join(' · ');q('#chosen-visit').hidden=!visitSettings();q('#copy-status').textContent='Uses your own AI account. Its limits and charges still apply.';q('#manual').open=false;setup.showModal();}
qa('[data-setup]').forEach(b=>b.addEventListener('click',showSetup));
q('[data-close]').addEventListener('click',()=>setup.close());
setup.addEventListener('close',()=>opener?.focus());
qa('[data-provider]').forEach(b=>b.addEventListener('click',()=>{provider=b.dataset.provider;qa('[data-provider]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));q('#provider-name').textContent=provider==='Other AI'?'your AI app':provider;q('#open-provider').textContent='Open '+provider+' ↗';q('#open-provider').href=provider==='Claude'?'https://claude.ai/':'https://chatgpt.com/';q('#open-provider').hidden=provider==='Other AI';}));
q('#copy-guide').addEventListener('click',async()=>{
 try{if(!navigator.clipboard?.writeText)throw Error('Clipboard unavailable');await navigator.clipboard.writeText(textToCopy());q('#copy-status').textContent='Copied. Paste the guide into a new conversation in '+(provider==='Other AI'?'your AI app':provider)+'.';}
 catch{q('#manual').open=true;q('#guide-text').focus();q('#guide-text').select();q('#copy-status').textContent='Clipboard unavailable. The full guide is selected below—copy it manually.';}
});
if(q('#art-view')){
 const view=q('#art-view');let trigger;
 q('#open-art').addEventListener('click',e=>{trigger=e.currentTarget;view.showModal();});
 q('#close-art').addEventListener('click',()=>view.close());
 view.addEventListener('close',()=>trigger?.focus());
 qa('[data-crop]').forEach(b=>b.addEventListener('click',()=>{qa('[data-crop]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));q('#art-frame').classList.toggle('closer',b.dataset.crop==='detail');q('#crop-note').textContent=b.dataset.crop==='detail'?'Cropped detail · Water Lilies, 1906':'Whole work · Water Lilies, 1906';}));
}
if(q('#off-visit-config')){
 function updateVisit(){
  const mode=q('[data-visit-mode][aria-pressed=true]').dataset.visitMode;
  q('#mission-title').textContent=visitModes[mode].title;
  q('#mission-copy').textContent=visitModes[mode].description;
  q('#duration-summary').textContent=q('#visit-minutes').value+' minutes';
  q('#museum-summary').textContent=q('#visit-museum').value.trim()||'Choose together';
  q('#interest-summary').textContent=q('#visit-interests').value.trim()||(mode==='theme'?'Choose a theme together':'Find what draws you in');
  q('#interests-label').textContent=mode==='theme'?'Your theme':'Your interests';
  q('#interest-summary-label').textContent=mode==='theme'?'THEME':'INTERESTS';
  q('#visit-interests').placeholder=mode==='theme'?'e.g. Myths and monsters, women artists, Impressionism':'e.g. Impressionism, sculpture, surprising stories';
 }
 qa('[data-visit-mode]').forEach(b=>b.addEventListener('click',()=>{qa('[data-visit-mode]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));updateVisit();}));
 qa('#off-visit-config input').forEach(input=>input.addEventListener('input',updateVisit));
 q('#visit-minutes').addEventListener('change',updateVisit);updateVisit();
}
if(q('#visit-config')){
 function updateTicket(){q('#pace-summary').textContent=q('[name=pace]:checked').dataset.label;q('#time-summary').textContent=q('[name=time]:checked').value+' minutes';}
 qa('#visit-config input').forEach(input=>input.addEventListener('change',updateTicket));updateTicket();
}
