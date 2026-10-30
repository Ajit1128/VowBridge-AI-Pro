'use strict';
const $ = id => document.getElementById(id);
const safe = value => String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const split = text => [...new Set(String(text).split(/[,\n;]/).map(x=>x.trim()).filter(Boolean))];
const roleLabel = {a:'FAMILY A',b:'FAMILY B',bridge:'SHARED'};
let preview = false;
let current = null;
let currentPayload = null;

function showMessage(message, success=false){$('messageBox').hidden=false;$('messageBox').className='notice'+(success?' success':'');$('messageBox').textContent=message;}
function setMode(isPreview){preview=isPreview;$('liveMode').classList.toggle('active',!preview);$('previewMode').classList.toggle('active',preview);$('modeExplanation').textContent=preview?'Synthetic fixtures only. Useful to explore UI; not real Qloo results.':'Queries Qloo for real artist identities and taste affinities.';}
$('liveMode').addEventListener('click',()=>setMode(false));
$('previewMode').addEventListener('click',()=>setMode(true));

async function status(){try{const response=await fetch('/api/health');const data=await response.json();$('connectionLabel').textContent=data.live_qloo_available?'Live Qloo configured':'Qloo key not configured';$('connectionSub').textContent=data.live_qloo_available?'Secure server connection ready':'Synthetic preview still available';$('connectionDot').classList.toggle('online',data.live_qloo_available);}catch{$('connectionLabel').textContent='Server connection error';$('connectionSub').textContent='Reload the app and retry';}}
status();
const timeLabel = min => `${String(Math.floor(min/60)).padStart(2,'0')}:${String(min%60).padStart(2,'0')}`;
function pills(items, className=''){return items.length?items.map(a=>`<span class="chip ${className}" title="Entity ID: ${safe(a.id)}">${safe(a.name)}</span>`).join(''):'<span class="chip">No supported overlap was found</span>';}
function render(data){
 current=data;
 $('output').hidden=false;
 $('resultMode').textContent=data.mode==='live-qloo'?'LIVE QLOO':'SYNTHETIC PREVIEW';
 $('scoreDuration').textContent=`${data.duration} min`;
 $('scoreA').textContent=`${Math.round(100*data.verification.a_minutes_equivalent/data.duration)}%`;
 $('scoreB').textContent=`${Math.round(100*data.verification.b_minutes_equivalent/data.duration)}%`;
 $('scoreNew').textContent=String(data.difference_from_no_qloo.new_recommendations_in_plan);
 $('sharedCount').textContent=String(data.difference_from_no_qloo.independently_shared_candidates);
 $('timelineStrip').innerHTML=data.timeline.map(s=>`<div class="${safe(s.side)}" style="flex:${Number(s.minutes)}" title="${safe(s.stage)}: ${safe(s.artist)} · ${Number(s.minutes)} min"></div>`).join('');
 $('timelineRows').innerHTML=data.timeline.map(s=>`<div class="slot-row"><span class="slot-time">${timeLabel(s.start_minute)}</span><div class="slot-data"><b>${safe(s.artist)}</b><small>${safe(s.stage)} · ${safe(s.reason)}</small></div><span class="slot-minutes">${Number(s.minutes)}m</span><span class="side-pill ${safe(s.side)}">${roleLabel[s.side]}</span><button class="ban-btn" data-ban="${safe(s.artist)}" title="Exclude artist and replan">×</button></div>`).join('');
 $('evidenceA').innerHTML=pills(data.taste_evidence.a);
 $('evidenceB').innerHTML=pills(data.taste_evidence.b);
 $('evidenceShared').innerHTML=pills(data.taste_evidence.shared,'mint');
 $('evidenceFoot').textContent=data.mode==='live-qloo'?'Names and IDs come from live Qloo responses. Shared candidates are present in both independent recommendation pools. This is a taste signal, not a prediction of attendance or enjoyment.':'SYNTHETIC PREVIEW: Invented artist fixtures. This mode does not use Qloo and cannot serve as proof of hackathon integration.';
 $('auditRows').innerHTML=data.verification.checks.map(c=>`<div class="audit-item"><span>${safe(c.name)}</span><i>${c.passed?'✓ PASSED':'✕ FAILED'}</i></div>`).join('');
 $('traceRows').innerHTML=data.agent_trace.map((s,i)=>`<div class="trace-step"><small>STEP ${String(i+1).padStart(2,'0')}</small><strong>${safe(s.action)}</strong><p>${safe(s.detail)}</p></div>`).join('');
 document.querySelectorAll('[data-ban]').forEach(btn=>btn.addEventListener('click',async ()=>{
   const artist=btn.getAttribute('data-ban');const old=split($('banned').value);if(!old.some(x=>x.toLowerCase()===artist.toLowerCase()))old.push(artist);
   $('banned').value=old.join(', ');
   showMessage(`${artist} has been excluded. Regenerating and re-verifying the program…`,true);
   await generate(true);
 }));
 setTimeout(()=>$('output').scrollIntoView({behavior:'smooth',block:'start'}),120);
}
async function generate(isReplan=false){
 const payload={group_a:split($('groupA').value),group_b:split($('groupB').value),banned:split($('banned').value),duration:Number($('duration').value),vibe:$('vibe').value,preview};
 if(!payload.group_a.length||!payload.group_b.length){showMessage('Please enter at least one favorite artist for each family.');return;}
 if(payload.group_a.length>4||payload.group_b.length>4){showMessage('Please use up to 4 artists per family.');return;}
 currentPayload=payload;
 $('generateBtn').disabled=true;$('generateBtn').querySelector('span').textContent=isReplan?'Rebuilding your program…':'Working on your program…';$('loadingSteps').hidden=false;$('messageBox').hidden=true;
 $('loadingText').textContent=preview?'Running the transparent synthetic preview…':'Resolving seeds and querying Qloo for each side and both together…';
 try{
   const response=await fetch('/api/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   const data=await response.json();
   if(!response.ok){let detail=data.detail||'Unexpected server error';if(typeof detail!=='string')detail=JSON.stringify(detail);throw new Error(detail);}
   if(!data.verification.passed)throw new Error('The independent verifier rejected the program.');
   render(data);
   if(data.unresolved.a.length||data.unresolved.b.length){showMessage(`Unrecognized artist names omitted: ${[...data.unresolved.a,...data.unresolved.b].join(', ')}. Please check the spelling.`,false);}
   else if(preview)showMessage('Preview only: every artist and affinity in this run is synthetic. Switch to Live Qloo to test genuine cultural intelligence.',true);
   else showMessage('Live Qloo results received. Program generated and all deterministic checks passed.',true);
 }catch(error){showMessage(error.message||String(error));$('messageBox').scrollIntoView({behavior:'smooth',block:'center'});}
 finally{$('generateBtn').disabled=false;$('generateBtn').querySelector('span').textContent='Generate cultural program';$('loadingSteps').hidden=true;}
}
$('plannerForm').addEventListener('submit',event=>{event.preventDefault();generate();});
function download(name,type,content){const blob=new Blob([content],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);}
$('downloadBtn').addEventListener('click',()=>{if(current)download('vowbridge-wedding-program.json','application/json',JSON.stringify(current,null,2));});
$('csvBtn').addEventListener('click',()=>{
 if(!current)return;
 const fields=['start_minute','minutes','stage','side','artist','entity_id','reason'];
 const escapeCSV=value=>'"'+String(value??'').replaceAll('"','""')+'"';
 const csv=[fields.join(','),...current.timeline.map(row=>fields.map(key=>escapeCSV(row[key])).join(','))].join('\r\n');
 download('vowbridge-dj-schedule.csv','text/csv;charset=utf-8','\ufeff'+csv);
});
