const canvas = document.querySelector("#world");
const ctx = canvas.getContext("2d");
const titleEl = document.querySelector("#inspect-title");
const badgesEl = document.querySelector("#inspect-badges");
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

const baseMarkers = [
  {
    x:330,y:330,r:18,title:"Six Nations Melted",layer:"past",status:"source-backed",
    summary:"The preserved 2025 corpus names this as the first Field Attestation Ceremony under the Bonfire Sky. This marker is a historical source tile, not a claim that the current rendering reproduces the event exactly.",
    source:"legacy/2025/Playable_Universe/PlayableWorld_Six_Nations_Melted.md"
  },
  {
    x:690,y:520,r:18,title:"Binbrook Hearth",layer:"past",status:"source-backed",
    summary:"A dense 2025 Playable World anchor: walks, bonfires, music, witness, Canon work and companion continuity.",
    source:"legacy/2025/Playable_Universe/PlayableWorld_Binbrook_Hearth.md"
  },
  {
    x:1480,y:350,r:24,title:"Make an Attest",layer:"present",status:"portal",
    summary:"Create a new explicit human claim from an ordinary phone. The first browser path binds text, optional local photo digest and optional coarse location, then earns a candidate receipt.",
    source:"docs/PHONE_ATTESTATION_PROTOCOL_V0.md",action:"../attest/"
  },
  {
    x:2380,y:300,r:20,title:"2041 — Transparent Authority",layer:"future",status:"illustrative",
    summary:"A projected branch in which consequential institutional authority becomes more legible and contestable. Illustrative only; not a forecast.",
    source:"data/tiles.json#future-transparent-authority-2041"
  },
  {
    x:2820,y:535,r:20,title:"2038 — The Glass Registry",layer:"future",status:"failure-branch",
    summary:"A failure scenario in which identity, rights, reputation and emergency powers collapse into a universal dossier. Reachable candidate for study; outside the design valley.",
    source:"data/tiles.json#future-orwellian-capture-2038"
  }
];
let markers = [...baseMarkers];

function hashPos(hex, offset=0) {
  const part=(hex || "abcd1234").slice(offset,offset+4).padEnd(4,"0");
  return parseInt(part,16)/65535;
}

async function loadFieldCandidates(){
  try{
    const r=await fetch("../api/v0/attestations/public?limit=40",{cache:"no-store"});
    if(!r.ok)return;
    const feed=await r.json();
    const live=feed.items.map((item,i)=>{
      const h=item.packet_sha256;
      return {
        x:1050 + hashPos(h,0)*760,
        y:180 + hashPos(h,4)*420,
        r:12,
        title:item.packet.claim.text.length>52 ? item.packet.claim.text.slice(0,49)+"…" : item.packet.claim.text,
        layer:"present",
        status:"self-attested / unverified",
        summary:(item.packet.witness.display_name || "Anonymous witness")+" attested: “"+item.packet.claim.text+"”",
        source:item.candidate_id,
        receipt:item.receipt_sha256
      };
    });
    markers=[...baseMarkers,...live];
  }catch(_){}
}
loadFieldCandidates();
setInterval(loadFieldCandidates,30000);

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
  if(p.x<-50||p.x>canvas.width+50)return;
  let fill=m.layer==="past"?"#8e3f2f":m.layer==="future"?"#4c654d":"#c69042";
  if(m.status==="failure-branch")fill="#642c27";
  if(m.status.includes("unverified"))fill="#d39b42";
  ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);
  ctx.fillStyle=fill;ctx.fill();
  ctx.lineWidth=Math.max(2,2*scale);ctx.strokeStyle="#f4ead5";ctx.stroke();
  ctx.font=`${Math.max(11,13*scale)}px ui-monospace,monospace`;
  ctx.fillStyle="#20231f";
  ctx.fillText(m.title,p.x+r+7,p.y+4);
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

  // distant ridges
  ctx.fillStyle="rgba(83,103,77,.32)";
  ctx.beginPath();ctx.moveTo(0,canvas.height*.52);
  for(let sx=0;sx<=canvas.width;sx+=70){
    const wx=cameraX+sx/scale;
    const y=(270+70*Math.sin(wx/250)+35*Math.sin(wx/95))*scale;
    ctx.lineTo(sx,y);
  }
  ctx.lineTo(canvas.width,canvas.height);ctx.lineTo(0,canvas.height);ctx.fill();

  // near valley floor
  ctx.fillStyle="rgba(76,101,77,.48)";
  ctx.beginPath();ctx.moveTo(0,canvas.height*.73);
  for(let sx=0;sx<=canvas.width;sx+=60){
    const wx=cameraX+sx/scale;
    const y=(520+42*Math.sin(wx/210))*scale;
    ctx.lineTo(sx,y);
  }
  ctx.lineTo(canvas.width,canvas.height);ctx.lineTo(0,canvas.height);ctx.fill();

  // temporal boundaries
  for(const x of [950,1950]){
    const sx=(x-cameraX)*scale;
    ctx.setLineDash([8*scale,8*scale]);ctx.strokeStyle="rgba(32,35,31,.28)";ctx.lineWidth=2*scale;
    ctx.beginPath();ctx.moveTo(sx,0);ctx.lineTo(sx,canvas.height);ctx.stroke();ctx.setLineDash([]);
  }

  // path
  ctx.strokeStyle="#d8bd82";ctx.lineWidth=26*scale;ctx.lineCap="round";
  ctx.beginPath();
  for(let x=0;x<=WORLD_W;x+=80){
    const p=worldToScreen(x,470+35*Math.sin(x/260),cameraX,scale);
    if(x===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);
  }
  ctx.stroke();

  // labels
  ctx.fillStyle="rgba(32,35,31,.48)";
  ctx.font=`800 ${18*scale}px ui-monospace,monospace`;
  [["ATTESTED PAST",300],["LIVE PRESENT",1320],["PROJECTED FUTURE",2380]].forEach(([t,x])=>{
    const sx=(x-cameraX)*scale;if(sx>-300&&sx<canvas.width+100)ctx.fillText(t,sx,90*scale);
  });

  markers.forEach(m=>drawMarker(m,cameraX,scale));

  // player
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
  badgesEl.innerHTML='<span class="badge">'+m.layer+'</span><span class="badge">'+m.status+'</span>';
  summaryEl.textContent=m.summary;
  sourceEl.textContent=m.source;
  actionEl.innerHTML=m.action?'<a href="'+m.action+'">Enter →</a>':"";
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

inspect(baseMarkers[2]);
