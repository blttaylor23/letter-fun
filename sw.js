const C="letter-fun-v14";
const L="abcdefghijklmnopqrstuvwxyz".split("");
// recorded voices (keep in step with VOICES in index.html; the page also asks us to cache any voice it lists)
const VOICE_DIRS=["voices/dad/"];
const PHRASE_FILES=["find","draw","draw_upper","draw_lower","yes","try_again","yes_great_job","keep_going","oops","all_green","speed_slow","speed_normal","speed_fast"];
const CORE=["./","index.html","manifest.json","icon-192.png","icon-512.png","icon-180.png"];
const MEDIA=L.map(l=>"sounds/"+l+".mp3").concat(...VOICE_DIRS.map(d=>L.map(l=>d+"names/"+l+".mp3").concat(L.map(l=>d+"sounds/"+l+".mp3"),PHRASE_FILES.map(p=>d+"phrases/"+p+".mp3"))));
// Install: core files must cache; an audio clip that fails to download must not break the whole install.
self.addEventListener("install",e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(CORE).then(()=>Promise.all(MEDIA.map(f=>c.add(f).catch(()=>{}))))));self.skipWaiting();});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))));self.clients.claim();});
// The page sends the full list of voice clips it may play: fetch any we don't have yet (quietly skip failures).
self.addEventListener("message",e=>{
  const d=e.data||{}; if(d.type!=="cache-voices"||!Array.isArray(d.files)) return;
  const files=d.files.filter(f=>typeof f==="string"&&/^voices\/[\w-]+\/(names|sounds|phrases)\/[\w-]+\.mp3$/.test(f)).slice(0,500);
  e.waitUntil(caches.open(C).then(c=>Promise.all(files.map(f=>c.match(f).then(h=>h||c.add(f).catch(()=>{}))))));
});
// Offline copy of an audio file for a Range request (iOS Safari always asks for byte ranges and needs a 206 back).
async function rangeFromCache(req){
  const hit=await caches.match(req.url,{ignoreSearch:true}); if(!hit) return undefined;
  const m=/bytes=(\d*)-(\d*)/.exec(req.headers.get("range")||""); if(!m) return hit;
  const buf=await hit.arrayBuffer(), size=buf.byteLength;
  let a=m[1]===""?Math.max(0,size-(+m[2]||0)):+m[1], b=(m[1]!==""&&m[2]!=="")?Math.min(+m[2],size-1):size-1;
  if(a>=size||a>b) return new Response("",{status:416,headers:{"Content-Range":"bytes */"+size}});
  return new Response(buf.slice(a,b+1),{status:206,headers:{"Content-Type":hit.headers.get("Content-Type")||"audio/mpeg","Content-Range":"bytes "+a+"-"+b+"/"+size,"Content-Length":String(b-a+1),"Accept-Ranges":"bytes"}});
}
// Network first (so updates show up), cache as the offline fallback. Only whole 200 responses are cached:
// cache.put() rejects partial (206) responses, which the audio clips often are.
self.addEventListener("fetch",e=>{
  const req=e.request; if(req.method!=="GET") return;
  const ranged=req.headers.has("range");
  e.respondWith(fetch(req).then(r=>{
    if(!ranged&&r.status===200&&r.type==="basic"){const cp=r.clone();caches.open(C).then(c=>c.put(req,cp)).catch(()=>{});}
    return r;
  }).catch(()=>ranged?rangeFromCache(req):caches.match(req).then(h=>h||(req.mode==="navigate"?caches.match("index.html"):undefined))));
});
