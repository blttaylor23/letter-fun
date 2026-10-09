// v25: family cloud sync (Firebase Realtime Database over REST + anonymous Firebase Auth; no SDK).
// Off (a no-op) until sync-config.js has a config. A device only reads or writes after it has been LINKED with the
// family sync password (a grown-up types it once per device; the database rules check it). Each device writes ONLY its
// own record (dev/<device uid>); everything else is merged on read, so nothing from another device is ever overwritten:
//   high scores = max, play time and right/wrong counts = sum of every device's OWN counters (no double counting),
//   players are matched by name, soft deletes win over older activity, resets are time-stamped.
(function(){
"use strict";
const CFG=window.LF_SYNC_CONFIG||null;
const ON=!!(CFG&&CFG.apiKey&&CFG.db&&CFG.fam);
const AK="lf-sync-auth";
function lsg(k,d){ try{ const v=localStorage.getItem(k); return v===null?d:JSON.parse(v); }catch(e){ return d; } }
function lss(k,v){ try{ localStorage.setItem(k,JSON.stringify(v)); }catch(e){} }
async function xf(url,opt,ms){ const ac=typeof AbortController!=="undefined"?new AbortController():null; const t=ac&&setTimeout(()=>ac.abort(),ms||12000);
  try{ return await fetch(url,Object.assign({cache:"no-store"},opt||{},ac?{signal:ac.signal}:{})); } finally{ if(t) clearTimeout(t); } }
const IDT=ON&&(CFG.authBase||"https://identitytoolkit.googleapis.com"), STK=ON&&(CFG.tokenBase||"https://securetoken.googleapis.com");
let tokP=null;
function token(){ if(!tokP) tokP=tokenNow().finally(()=>{ tokP=null; }); return tokP; }
async function tokenNow(){
  let a=lsg(AK,null);
  if(a&&a.id&&a.exp>Date.now()+120000) return a;
  if(a&&a.rt){
    const r=await xf(STK+"/v1/token?key="+encodeURIComponent(CFG.apiKey),{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:"grant_type=refresh_token&refresh_token="+encodeURIComponent(a.rt)});
    if(r.ok){ const j=await r.json(); a={uid:j.user_id,rt:j.refresh_token,id:j.id_token,exp:Date.now()+(+j.expires_in||3600)*1000,linked:!!a.linked}; lss(AK,a); return a; }
    if(r.status<400||r.status>=500) throw new Error("token refresh "+r.status);
    a=null; // the anonymous user is gone: start again (this device has to be linked again)
  }
  const r=await xf(IDT+"/v1/accounts:signUp?key="+encodeURIComponent(CFG.apiKey),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({returnSecureToken:true})});
  if(!r.ok) throw new Error("sign-in "+r.status);
  const j=await r.json(); a={uid:j.localId,rt:j.refreshToken,id:j.idToken,exp:Date.now()+(+j.expiresIn||3600)*1000,linked:false}; lss(AK,a); return a; }
function url(path,a){ return CFG.db.replace(/\/$/,"")+"/lf/"+encodeURIComponent(CFG.fam)+(path?"/"+path:"")+".json?"+(a?"auth="+encodeURIComponent(a.id)+"&":"")+(CFG.dbq||""); }
async function req(method,path,body,auth){ const a=auth===false?null:await token();
  const r=await xf(url(path,a),{method,headers:body!==undefined?{"Content-Type":"application/json"}:{},body:body!==undefined?JSON.stringify(body):undefined,keepalive:method!=="GET"&&JSON.stringify(body||"").length<60000});
  if(r.status===401||r.status===403){ const e=new Error("denied"); e.denied=true; throw e; }
  if(!r.ok) throw new Error(method+" "+path+" "+r.status);
  return r.json(); }
async function hash(pw){ const d=new TextEncoder().encode("letter-fun|"+CFG.fam+"|"+String(pw));
  const b=await crypto.subtle.digest("SHA-256",d); return [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,"0")).join(""); }
function status(){ const a=lsg(AK,null); return {on:ON, linked:!!(ON&&a&&a.linked), uid:a&&a.uid||null}; }
async function hasPassword(){ return (await req("GET","has",undefined,false))===true; }
// link this device (or the parent page) to the family: create=true sets the family sync password the very first time
async function link(pw,create){
  if(!ON) throw new Error("off"); pw=String(pw||""); if(pw.length<6) { const e=new Error("short"); e.short=true; throw e; }
  const a=await token(), h=await hash(pw);
  if(create){ try{ await req("PATCH","",{ph:h,has:true}); }catch(e){ if(e.denied){ const x=new Error("exists"); x.exists=true; throw x; } throw e; } }
  try{ await req("PUT","members/"+a.uid,{h,t:Date.now()}); }catch(e){ if(e.denied){ const x=new Error("wrong"); x.wrong=true; throw x; } throw e; }
  const b=lsg(AK,a); b.linked=true; lss(AK,b); return true; }
async function unlink(){ const a=lsg(AK,null); if(ON&&a&&a.linked){ try{ await req("DELETE","members/"+a.uid); }catch(e){} } if(a){ a.linked=false; lss(AK,a); } }
async function checkLinked(){ if(!ON) return false; const a=await token(); const m=await req("GET","members/"+a.uid).catch(e=>{ if(e.denied) return null; throw e; });
  const b=lsg(AK,a); b.linked=!!m; lss(AK,b); return b.linked; }
async function putDevice(rec){ const a=await token(); return req("PUT","dev/"+a.uid,rec); }
async function getAll(){ return (await req("GET","dev"))||{}; }
// ---------- merging (pure) ----------
const nm=s=>String(s||"").replace(/\s+/g," ").trim().toLowerCase();
const num=v=>{ v=+v; return isFinite(v)&&v>0?v:0; };
function emptyTime(){ return {total:0,days:{},games:{},last:0}; }
function addTime(a,b){ const r={total:num(a&&a.total)+num(b&&b.total),days:{},games:{},last:Math.max(num(a&&a.last),num(b&&b.last))};
  for(const x of [a,b]) if(x){ for(const k in x.days||{}) r.days[k]=(r.days[k]||0)+num(x.days[k]); for(const k in x.games||{}) r.games[k]=(r.games[k]||0)+num(x.games[k]); } return r; }
function addProg(a,b){ const items={};
  for(const x of [a,b]) for(const k in (x&&x.items)||{}){ const v=x.items[k]; if(!v) continue; const it=items[k]||(items[k]={r:0,w:0,c:{}}); it.r+=num(v.r); it.w+=num(v.w); for(const t in v.c||{}) it.c[t]=(it.c[t]||0)+num(v.c[t]); }
  return {items}; }
function maxBest(a,b){ const r=Object.assign({},a||{}); for(const g in b||{}) r[g]=Math.max(num(r[g]),num(b[g])); return r; }
// every device's entries grouped by player name: {name: [{dev, label, seen, e}]}
function groups(devs){ const g={};
  for(const dv in devs||{}){ const rec=devs[dv]; if(!rec||typeof rec!=="object") continue;
    for(const k in rec.players||{}){ const e=rec.players[k]; if(!e||!e.n) continue; const n=nm(e.n); (g[n]||(g[n]=[])).push({dev:dv,label:rec.label||"",seen:num(rec.seen),key:k,e}); } }
  return g; }
// one name across devices: alive? (newest activity vs newest delete), newest resets, display name, created
function nameState(list){ let alive=0, del=0, perm=false, rb={}, rp=0, c=0, name="";
  for(const {e} of list){ if(e.perm) perm=true; if(num(e.d)) del=Math.max(del,num(e.d)); else { const s=Math.max(num(e.s),num(e.c),num(e.t&&e.t.last)); if(s>=alive){ alive=s; name=e.n; } }
    for(const g in e.br||{}) rb[g]=Math.max(num(rb[g]),num(e.br[g])); rp=Math.max(rp,num(e.pr)); if(num(e.c)&&(!c||num(e.c)<c)) c=num(e.c); }
  if(!name&&list.length) name=list[0].e.n;
  return {alive:perm||alive>del, deletedAt:del, rb, rp, created:c, name, perm}; }
// the sum of the given entries (only live ones, and only counters that already applied the newest resets)
function combine(list,st){ let time=emptyTime(), prog={items:{}}, best={};
  for(const {e} of list){ if(num(e.d)) continue; time=addTime(time,e.t); if(num(e.pr)>=st.rp) prog=addProg(prog,e.p);
    for(const g in e.b||{}) if(num(e.br&&e.br[g])>=num(st.rb[g])) best[g]=Math.max(num(best[g]),num(e.b[g])); }
  return {time,prog,best}; }
// the parent page: everyone, merged by name
function summary(devs){ const G=groups(devs), out=[]; let total=emptyTime();
  for(const n in G){ const list=G[n], st=nameState(list), live=list.filter(x=>!num(x.e.d)), all=combine(list.map(x=>({e:Object.assign({},x.e,{d:0})})),st);
    total=addTime(total,all.time); // every minute ever played counts in the family total, deleted players too
    const c=combine(list,st);
    const used=st.alive?live:list, played=used.filter(x=>num(x.e.t&&x.e.t.total)>0||Object.keys((x.e.p&&x.e.p.items)||{}).length);
    out.push({name:st.name, key:n, alive:st.alive, deletedAt:st.deletedAt, created:st.created, devices:new Set(played.map(x=>x.dev)).size, profiles:new Set(used.map(x=>x.dev)).size,
      perDevice:(st.alive?live:list).map(x=>({dev:x.dev,label:x.label,seen:x.seen,total:num(x.e.t&&x.e.t.total),last:num(x.e.t&&x.e.t.last),deleted:!!num(x.e.d)})),
      time:st.alive?c.time:all.time, prog:st.alive?c.prog:all.prog, best:st.alive?c.best:all.best}); }
  out.sort((a,b)=>(b.alive-a.alive)||(b.time.total-a.time.total)||a.name.localeCompare(b.name));
  return {players:out, total, devices:Object.keys(devs||{}).length}; }
window.LFSync={ON,CFG,status,hasPassword,link,unlink,checkLinked,putDevice,getAll,token,nm,num,emptyTime,addTime,addProg,maxBest,groups,nameState,combine,summary};
})();
