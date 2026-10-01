const C="letter-fun-v20";            // app shell (index.html, icons ...): replaced on every release
const A="letter-fun-audio-2";        // recorded clips: kept across releases (bump only when clips change), filled lazily
const L="abcdefghijklmnopqrstuvwxyz".split("");
const VOICE_DIRS=["voices/dad/"];   // safety net only: the page sends the full list (every voice, the selected one first)
const PHRASE_FILES=["find","draw","draw_upper","draw_lower","yes","try_again","yes_great_job","keep_going","oops","all_green","speed_slow","speed_normal","speed_fast","nope_a","nope_an"];
const CORE=["./","index.html","manifest.json","icon-192.png","icon-512.png","icon-180.png"];
const JOINED=["find","draw_upper","draw_lower","nope_a","nope_an"];
const MEDIA=L.map(l=>"sounds/"+l+".mp3").concat(...VOICE_DIRS.map(d=>L.map(l=>d+"names/"+l+".mp3").concat(L.map(l=>d+"sounds/"+l+".mp3"),PHRASE_FILES.map(p=>d+"phrases/"+p+".mp3"),...JOINED.map(p=>L.map(l=>d+"prompts/"+p+"_"+l+".mp3")))));
const fresh=f=>new Request(f,{cache:"reload"});
// v17: install caches ONLY the small app shell, so a new version is ready in a second or two. (v16 downloaded ~175
// clips all at once here, which on a slow connection held up the first launch and starved the sounds the page needed.)
self.addEventListener("install",e=>{ self.skipWaiting(); e.waitUntil(caches.open(C).then(c=>c.addAll(CORE.map(fresh)))); });
self.addEventListener("activate",e=>{ e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C&&x!==A).map(x=>caches.delete(x)))).then(()=>self.clients.claim())); });
// Clips are cached in the background, a few at a time, after the page has loaded (the page sends the list).
// which clips are in the audio cache (so a fetch can decide right away whether to answer or let the browser load it)
let known=null;
const loadKnown=()=>caches.open(A).then(c=>c.keys()).then(ks=>{ known=new Set(ks.map(r=>new URL(r.url).pathname)); }).catch(()=>{ known=new Set(); });
loadKnown();
// v18: the newest list wins, so after a voice switch that voice's clips are fetched next, even mid-fill.
let filling=null, want=[];
function fillAudio(files){
  want=files.slice();
  if(filling) return filling;
  filling=caches.open(A).then(async c=>{
    const worker=async()=>{ for(let f=want.shift();f;f=want.shift()){ const path=new URL(f,self.registration.scope).pathname;
      if(known&&known.has(path)) continue; if(await c.match(f)){ if(known) known.add(path); continue; }
      try{ const r=await fetch(fresh(f)); if(r.status===200){ await c.put(f,r); if(known) known.add(path); } }catch(e){} } };
    await Promise.all([worker(),worker(),worker()]);
  }).catch(()=>{}).then(()=>{ filling=null; });
  return filling;
}
self.addEventListener("message",e=>{
  const d=e.data||{}; if(d.type!=="cache-voices"||!Array.isArray(d.files)) return;
  const ok=f=>typeof f==="string"&&(/^voices\/[\w-]+\/(names|sounds|phrases|prompts)\/[\w-]+\.mp3$/.test(f)||/^sounds\/[a-z]\.mp3$/.test(f));
  e.waitUntil(fillAudio(d.files.filter(ok).concat(MEDIA).filter((f,i,a)=>a.indexOf(f)===i).slice(0,800)));
});
// A cached clip, answered the way iOS Safari needs: it asks for byte ranges and must get a 206 with Content-Range.
async function fromAudioCache(req){
  const hit=await caches.open(A).then(c=>c.match(req.url,{ignoreSearch:true})); if(!hit) return null;
  const buf=await hit.arrayBuffer(), size=buf.byteLength, type="audio/mpeg";
  const m=/bytes=(\d*)-(\d*)/.exec(req.headers.get("range")||"");
  if(!m) return new Response(buf,{status:200,headers:{"Content-Type":type,"Content-Length":String(size),"Accept-Ranges":"bytes"}});
  let a=m[1]===""?Math.max(0,size-(+m[2]||0)):+m[1], b=(m[1]!==""&&m[2]!=="")?Math.min(+m[2],size-1):size-1;
  if(a>=size||a>b) return new Response("",{status:416,headers:{"Content-Range":"bytes */"+size}});
  return new Response(buf.slice(a,b+1),{status:206,headers:{"Content-Type":type,"Content-Range":"bytes "+a+"-"+b+"/"+size,"Content-Length":String(b-a+1),"Accept-Ranges":"bytes"}});
}
self.addEventListener("fetch",e=>{
  const req=e.request; if(req.method!=="GET") return;
  const url=new URL(req.url); if(url.origin!==location.origin) return;
  const path=url.pathname;
  // audio: cached copy if we have it; a clip we know isn't cached yet is NOT intercepted - the browser loads it natively (proper range requests)
  if(/\.mp3$/.test(path)){
    if(!known||known.has(path)) e.respondWith(fromAudioCache(req).then(r=>r||fetch(req)).catch(()=>fetch(req)));
    return;
  }
  // app shell / navigation: cache first (opens instantly, even on a bad connection), refreshed in the background
  if(req.mode==="navigate"||CORE.some(f=>path.endsWith("/"+f)||(f==="./"&&path.endsWith("/")))){
    const key=req.mode==="navigate"?"index.html":req;
    const net=fetch(fresh(req.mode==="navigate"?"index.html":req.url)).then(r=>{ if(r.status===200){ const cp=r.clone(); caches.open(C).then(c=>c.put(key,cp)).catch(()=>{}); } return r; });
    e.respondWith(caches.open(C).then(c=>c.match(key,{ignoreSearch:true})).then(hit=>{ if(hit){ e.waitUntil(net.catch(()=>{})); return hit; } return net; }).catch(()=>net));
    return;
  }
  // anything else: network, cache as the offline fallback
  e.respondWith(fetch(req).catch(()=>caches.match(req,{ignoreSearch:true}).then(h=>h||Response.error())));
});
