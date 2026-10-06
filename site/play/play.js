const canvas = document.querySelector("#world");
const ctx = canvas.getContext("2d");
const titleEl = document.querySelector("#inspect-title");
const badgesEl = document.querySelector("#inspect-badges");
const mediaEl = document.querySelector("#inspect-media");
const summaryEl = document.querySelector("#inspect-summary");
const sourceEl = document.querySelector("#inspect-source");
const actionEl = document.querySelector("#inspect-action");
const coordsEl = document.querySelector("#coords");
const modeLabel = document.querySelector("#mode-label");
const modeDot = document.querySelector("#mode-dot");

const WORLD_W = 3200;
const WORLD_H = 820;
const player = {x:1500,y:430,r:13};
const keys = new Set();
const touchKeys = new Set();
let lastTime = performance.now();

const portalMarker = {
  x:1500,y:350,r:24,title:"Make an Attest",layer:"present",status:"portal",
  summary:"Create a new explicit human claim from an ordinary phone. Text, optional evidence digest and optional coarse location become a candidate receipt before any later verification or Canon promotion.",
  source:"docs/PHONE_ATTESTATION_PROTOCOL_V0.md",
  action:"../attest/",
  media:[]
};

let markers = [portalMarker];

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  })[ch]);
}

function hashString(str) {
  let h = 2166136261 >>> 0;
  for (let i=0;i<str.length;i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h,16777619) >>> 0;
  }
  return h >>> 0;
}

function markerPosition(id, layer) {
  const h=hashString(id);
  const y=190 + ((h >>> 9) % 370);
  if(layer==="past") return {x:220 + (h % 620), y};
  if(layer==="future") return {x:2100 + (h % 850), y};
  return {x:1050 + (h % 760), y};
}

function tileToMarker(tile) {
  const pos=markerPosition(tile.id,tile.layer);
  return {
    ...pos,
    r:18,
    title:tile.title,
    layer:tile.layer,
    status:tile.status,
    summary:tile.summary,
    source:tile.source_ref || "world tile",
    action:null,
    media:[],
    designValley:tile.design_valley
  };
}

function eventsToMarkers(events) {
  const grouped = new Map();

  for (const event of events) {
    const p = event.payload || {};
    const candidateId = p.candidate_id || event.targets?.[0] || event.event_id;
    if (!grouped.has(candidateId)) {
      grouped.set(candidateId, {
        candidateId,
        received:null,
        lifecycle:[],
        media:[],
        evidenceSummary:null
      });
    }
    const group = grouped.get(candidateId);
    group.lifecycle.push(event);
    if (event.event_type === "attestation.candidate_received") {
      group.received = event;
    }
    if (Array.isArray(p.media) && p.media.length) {
      group.media = p.media;
    }
    if (p.evidence_summary) {
      group.evidenceSummary = p.evidence_summary;
    }
  }

  return [...grouped.values()].map(group => {
    const base = group.received || group.lifecycle[0] || {};
    const p = base.payload || {};
    const claim = p.claim?.text || "Public field candidate";
    const who = p.witness?.display_name || "Anonymous witness";
    const pos = markerPosition(group.candidateId,"present");
    const summary = group.evidenceSummary || {};
    let evidenceNote = "";
    if ((summary.public_derivative_count || 0) > 0) {
      evidenceNote = " Public evidence is available.";
    } else if ((summary.private_retained_count || 0) > 0) {
      evidenceNote = " The exact source image is preserved privately.";
    } else if ((summary.source_unavailable_reported_count || 0) > 0) {
      evidenceNote = " The bound source image was later reported unavailable.";
    } else if ((summary.bound_photo_count || 0) > 0) {
      evidenceNote = " A photo digest is bound, but FC does not retain the bytes.";
    }

    return {
      ...pos,
      r:12,
      title:claim.length>58 ? claim.slice(0,55)+"…" : claim,
      layer:"present",
      status:"self-attested / unverified",
      summary:who+" attested: “"+claim+"”"+evidenceNote,
      source:group.candidateId,
      action:null,
      media:group.media,
      assurance:p.assurance?.class || "browser-self-asserted",
      lifecycle:group.lifecycle,
      evidenceSummary:summary
    };
  });
}

async function loadWorld() {
  try {
    const [tilesResponse,eventsResponse] = await Promise.all([
      fetch("../api/v0/world/tiles",{cache:"no-store"}),
      fetch("../api/v0/scenes/present-room/events",{cache:"no-store"})
    ]);
    if(!tilesResponse.ok) throw new Error("tiles HTTP "+tilesResponse.status);
    if(!eventsResponse.ok) throw new Error("events HTTP "+eventsResponse.status);
    const tiles=await tilesResponse.json();
    const events=await eventsResponse.json();
    const tileMarkers=(tiles.items || []).map(tileToMarker);
    const eventMarkers=eventsToMarkers(events.items || []);
    markers=[...tileMarkers,portalMarker,...eventMarkers];
  } catch(err) {
    console.warn("World API unavailable; keeping local portal only",err);
    markers=[portalMarker];
  }
}
loadWorld();
setInterval(loadWorld,30000);

function region(x){
  if(x<950)return {name:"PLAYABLE PAST",short:"past",color:"#8e3f2f"};
  if(x<1950)return {name:"PLAYABLE PRESENT",short:"present",color:"#c69042"};
  return {name:"PLAYABLE FUTURE",short:"future",color:"#4c654d"};
}

function resizeBacking(){
  const rect=canvas.getBoundingClientRect();
  const dpr=Math.min(window.devicePixelRatio||1,2);
  const w=Math.max(640,Math.floor(rect.width*dpr));
  const h=Math.floor(w*610/1100);
  if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
}
window.addEventListener("resize",resizeBacking);

function worldToScreen(wx,wy,cameraX,scale){
  return {x:(wx-cameraX)*scale,y:wy*scale};
}

function drawMarker(m,cameraX,scale){
  const p=worldToScreen(m.x,m.y,cameraX,scale);
  const r=m.r*scale;
  if(p.x<-80||p.x>canvas.width+80)return;
  let fill=m.layer==="past"?"#8e3f2f":m.layer==="future"?"#4c654d":"#c69042";
  if(m.status==="failure-branch" || m.designValley==="outside")fill="#642c27";
  if(String(m.status).includes("unverified"))fill="#d39b42";
  ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);
  ctx.fillStyle=fill;ctx.fill();
  ctx.lineWidth=Math.max(2,2*scale);ctx.strokeStyle="#f4ead5";ctx.stroke();
  ctx.font=`${Math.max(11,13*scale)}px ui-monospace,monospace`;
  ctx.fillStyle="#20231f";
  ctx.fillText(m.title,p.x+r+7,p.y+4);
  if((m.media||[]).length){
    ctx.fillStyle="#fff3d0";
    ctx.beginPath();ctx.arc(p.x+r*.45,p.y-r*.45,4*scale,0,Math.PI*2);ctx.fill();
  }
}

function draw(){
  resizeBacking();
  const scale=canvas.height/WORLD_H;
  const viewportW=canvas.width/scale;
  const cameraX=Math.max(0,Math.min(WORLD_W-viewportW,player.x-viewportW/2));
  ctx.clearRect(0,0,canvas.width,canvas.height);

  function zone(x0,x1,color){
    const a=(x0-cameraX)*scale,b=(x1-cameraX)*scale;
    ctx.fillStyle=color;ctx.fillRect(a,0,b-a,canvas.height);
  }
  zone(0,950,"#ead3b0");zone(950,1950,"#e9ddb9");zone(1950,WORLD_W,"#d7d8b7");

  ctx.fillStyle="rgba(83,103,77,.32)";
  ctx.beginPath();ctx.moveTo(0,canvas.height*.52);
  for(let sx=0;sx<=canvas.width;sx+=70){
    const wx=cameraX+sx/scale;
    const y=(270+70*Math.sin(wx/250)+35*Math.sin(wx/95))*scale;
    ctx.lineTo(sx,y);
  }
  ctx.lineTo(canvas.width,canvas.height);ctx.lineTo(0,canvas.height);ctx.fill();

  ctx.fillStyle="rgba(76,101,77,.48)";
  ctx.beginPath();ctx.moveTo(0,canvas.height*.73);
  for(let sx=0;sx<=canvas.width;sx+=60){
    const wx=cameraX+sx/scale;
    const y=(520+42*Math.sin(wx/210))*scale;
    ctx.lineTo(sx,y);
  }
  ctx.lineTo(canvas.width,canvas.height);ctx.lineTo(0,canvas.height);ctx.fill();

  for(const x of [950,1950]){
    const sx=(x-cameraX)*scale;
    ctx.setLineDash([8*scale,8*scale]);ctx.strokeStyle="rgba(32,35,31,.28)";ctx.lineWidth=2*scale;
    ctx.beginPath();ctx.moveTo(sx,0);ctx.lineTo(sx,canvas.height);ctx.stroke();ctx.setLineDash([]);
  }

  ctx.strokeStyle="#d8bd82";ctx.lineWidth=26*scale;ctx.lineCap="round";
  ctx.beginPath();
  for(let x=0;x<=WORLD_W;x+=80){
    const p=worldToScreen(x,470+35*Math.sin(x/260),cameraX,scale);
    if(x===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);
  }
  ctx.stroke();

  ctx.fillStyle="rgba(32,35,31,.48)";
  ctx.font=`800 ${18*scale}px ui-monospace,monospace`;
  [["ATTESTED PAST",300],["LIVE PRESENT",1320],["PROJECTED FUTURE",2380]].forEach(([t,x])=>{
    const sx=(x-cameraX)*scale;if(sx>-300&&sx<canvas.width+100)ctx.fillText(t,sx,90*scale);
  });

  markers.forEach(m=>drawMarker(m,cameraX,scale));

  const pp=worldToScreen(player.x,player.y,cameraX,scale);
  ctx.beginPath();ctx.arc(pp.x,pp.y,player.r*scale,0,Math.PI*2);
  ctx.fillStyle="#20231f";ctx.fill();
  ctx.strokeStyle="#fff3d0";ctx.lineWidth=4*scale;ctx.stroke();
  ctx.font=`800 ${12*scale}px ui-monospace,monospace`;ctx.fillStyle="#20231f";
  ctx.fillText("you",pp.x+18*scale,pp.y-13*scale);

  const reg=region(player.x);
  coordsEl.textContent="x "+Math.round(player.x)+" · "+reg.short;
  modeLabel.textContent=reg.name;
  modeDot.style.background=reg.color;
}

function nearestMarker(max=110){
  let best=null,bestD=Infinity;
  for(const m of markers){
    const d=Math.hypot(m.x-player.x,m.y-player.y);
    if(d<bestD){best=m;bestD=d;}
  }
  return bestD<=max?best:null;
}

function inspect(m){
  if(!m)return;
  titleEl.textContent=m.title;
  badgesEl.innerHTML=
    '<span class="badge">'+esc(m.layer)+'</span>'+
    '<span class="badge">'+esc(m.status)+'</span>'+
    (m.designValley && m.designValley!=="not_applicable"
      ? '<span class="badge">design '+esc(m.designValley)+'</span>' : "");
  summaryEl.textContent=m.summary;
  sourceEl.textContent=m.source;
  actionEl.innerHTML=m.action?'<a href="'+esc(m.action)+'">Enter →</a>':"";
  const media=(m.media||[])[0];
  const lifecycle = m.lifecycle || [];
  const lastLifecycle = lifecycle.length
    ? lifecycle[lifecycle.length - 1]
    : null;
  let lifecycleNote = "";
  if (lastLifecycle && lastLifecycle.event_type !== "attestation.candidate_received") {
    lifecycleNote =
      '<p class="media-note">Latest lifecycle event: ' +
      esc(lastLifecycle.event_type) +
      ' · ' +
      esc(new Date(lastLifecycle.recorded_at).toLocaleString()) +
      '</p>';
  }
  if(media?.url){
    mediaEl.innerHTML=
      '<img src="'+esc(media.url)+'" alt="Published evidence derivative">'+
      '<p class="media-note">Published derivative · source digest remains bound in the attestation.</p>'+
      lifecycleNote;
  }else{
    mediaEl.innerHTML=lifecycleNote;
  }
}

function step(now){
  const dt=Math.min((now-lastTime)/1000,.05);lastTime=now;
  const speed=250;
  const active=k=>keys.has(k)||touchKeys.has(k);
  let dx=0,dy=0;
  if(active("left")||active("ArrowLeft")||active("a"))dx-=1;
  if(active("right")||active("ArrowRight")||active("d"))dx+=1;
  if(active("up")||active("ArrowUp")||active("w"))dy-=1;
  if(active("down")||active("ArrowDown")||active("s"))dy+=1;
  if(dx&&dy){dx*=.707;dy*=.707}
  player.x=Math.max(25,Math.min(WORLD_W-25,player.x+dx*speed*dt));
  player.y=Math.max(150,Math.min(690,player.y+dy*speed*dt));
  draw();requestAnimationFrame(step);
}
requestAnimationFrame(step);

window.addEventListener("keydown",e=>{
  const k=e.key.length===1?e.key.toLowerCase():e.key;
  keys.add(k);
  if(["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(k))e.preventDefault();
  if(k==="e")inspect(nearestMarker());
});
window.addEventListener("keyup",e=>keys.delete(e.key.length===1?e.key.toLowerCase():e.key));

document.querySelectorAll("[data-dir]").forEach(btn=>{
  const d=btn.dataset.dir;
  const on=e=>{e.preventDefault();touchKeys.add(d)};
  const off=e=>{e.preventDefault();touchKeys.delete(d)};
  btn.addEventListener("pointerdown",on);
  btn.addEventListener("pointerup",off);
  btn.addEventListener("pointercancel",off);
  btn.addEventListener("pointerleave",off);
});
document.querySelector("#interact").addEventListener("click",()=>inspect(nearestMarker()));

canvas.addEventListener("click",e=>{
  const rect=canvas.getBoundingClientRect();
  const scale=canvas.height/WORLD_H;
  const viewportW=canvas.width/scale;
  const cameraX=Math.max(0,Math.min(WORLD_W-viewportW,player.x-viewportW/2));
  const sx=(e.clientX-rect.left)*(canvas.width/rect.width);
  const sy=(e.clientY-rect.top)*(canvas.height/rect.height);
  let best=null,bestD=Infinity;
  for(const m of markers){
    const p=worldToScreen(m.x,m.y,cameraX,scale);
    const d=Math.hypot(p.x-sx,p.y-sy);
    if(d<bestD){best=m;bestD=d;}
  }
  if(bestD<45*Math.max(scale,.7))inspect(best);
});

inspect(portalMarker);
