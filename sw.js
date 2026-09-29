const C="letter-fun-v12";const F=["./","index.html","manifest.json","icon-192.png","icon-512.png","icon-180.png","sounds/a.mp3","sounds/b.mp3","sounds/c.mp3","sounds/d.mp3","sounds/e.mp3","sounds/f.mp3","sounds/g.mp3","sounds/h.mp3","sounds/i.mp3","sounds/j.mp3","sounds/k.mp3","sounds/l.mp3","sounds/m.mp3","sounds/n.mp3","sounds/o.mp3","sounds/p.mp3","sounds/q.mp3","sounds/r.mp3","sounds/s.mp3","sounds/t.mp3","sounds/u.mp3","sounds/v.mp3","sounds/w.mp3","sounds/x.mp3","sounds/y.mp3","sounds/z.mp3"];
// Install: core files must cache; a sound clip that fails to download must not break the whole install.
self.addEventListener("install",e=>{e.waitUntil(caches.open(C).then(c=>{const core=F.filter(f=>!f.startsWith("sounds/")),snd=F.filter(f=>f.startsWith("sounds/"));return c.addAll(core).then(()=>Promise.all(snd.map(f=>c.add(f).catch(()=>{}))));}));self.skipWaiting();});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))));self.clients.claim();});
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
