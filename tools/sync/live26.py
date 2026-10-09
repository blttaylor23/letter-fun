# v24 promotion checks. Usage: live.py upgrade|root BASE engines
#  upgrade: BASE serves a symlink /tmp/srvup/letter-fun -> old v22 tree; we load it, then swap to the new tree and relaunch.
#  root:    BASE is the live root (local or Pages): screens, voices (200s, no 404s), correct.mp3, offline, screenshots.
import asyncio,sys,os,json
from playwright.async_api import async_playwright
MODE=sys.argv[1]; BASE=sys.argv[2]; ENG=sys.argv[3].split(",") if len(sys.argv)>3 else ["chromium","webkit"]
SHOTS="/workspace/letter-fun-shots/"; TAG=sys.argv[4] if len(sys.argv)>4 else "live"
fails=[]
def check(c,m):
    print(("  ok   " if c else "  FAIL ")+m,flush=True)
    if not c: fails.append(m)
async def upgrade(p,eng):
    os.system("ln -sfn /tmp/oldlf /tmp/srvup/letter-fun")
    br=await getattr(p,eng).launch(); ctx=await br.new_context(viewport={"width":1180,"height":820}); pg=await ctx.new_page(); ev=pg.evaluate
    await pg.goto(BASE+"beta/"); await pg.wait_for_timeout(3000)   # the beta was used on this device too
    await ev("""localStorage.setItem('lf-players',JSON.stringify([{id:'p1',name:'Blakeli'},{id:'p2',name:'Little Bobby'}])); localStorage.setItem('lf-player','p1');
      localStorage.setItem('lf-best:p1',JSON.stringify({upper:7,num:5,fingers:3,drawnum:2})); localStorage.setItem('lf-prog:p1',JSON.stringify({items:{'L:b':{r:3,w:2}}}));""")
    await pg.goto(BASE); await pg.wait_for_timeout(3500)
    v=await ev("[!!document.getElementById('goABC'), navigator.serviceWorker.controller&&navigator.serviceWorker.controller.scriptURL]")
    await ev("localStorage.setItem('lf-voice-who','dad'); localStorage.setItem('lf-problem',JSON.stringify(['b','d'])); localStorage.setItem('lf-choices','6'); localStorage.setItem('lf-voice','normal')")
    k0=await ev("caches.keys()")
    check(v[0]==True and k0 and "letter-fun-v25" in k0, f"{eng} before: v25 live app installed {v} {k0}")
    ls0=await ev("JSON.stringify(Object.fromEntries(Object.keys(localStorage).sort().map(k=>[k,localStorage.getItem(k)])))")
    os.system("ln -sfn /workspace/letter-fun /tmp/srvup/letter-fun")   # Pages deploys v24
    await pg.goto(BASE); await pg.wait_for_timeout(5000)   # 1st launch: old page, the worker update installs in the background
    await pg.goto(BASE); await pg.wait_for_timeout(2500)   # 2nd launch
    r=await ev("[!!document.getElementById('goABC'), document.getElementById('who').classList.contains('on'), navigator.serviceWorker.controller&&navigator.serviceWorker.controller.scriptURL]")
    k1=await ev("caches.keys()")
    check(r[0] and r[1] and r[2].endswith("/letter-fun/sw.js"), f"{eng} after relaunch: v24 live app (Who's playing?), root worker in control {r}")
    check("letter-fun-v26" in k1 and "letter-fun-v25" not in k1 and "letter-fun-audio-2" in k1 and any(k.startswith("letter-fun-beta-") for k in k1), f"{eng} caches: new letter-fun-v26, old v24 deleted, beta + clip caches kept {k1}")
    sy=await ev("[!!document.getElementById('pSync'), typeof LFSync, LFSync.ON]")
    check(sy==[True,"object",True], f"{eng} v26 live: Family sync present and switched on (configured) {sy}")
    ls1=await ev("JSON.stringify(Object.fromEntries(Object.keys(localStorage).sort().map(k=>[k,localStorage.getItem(k)])))")
    a=json.loads(ls0); b=json.loads(ls1)
    pl=lambda x: json.dumps([[q["id"],q["name"]] for q in json.loads(x)])
    lost=[k for k in a if k not in b or (a[k]!=b[k] and not k.startswith('lf-time') and not (k=='lf-players' and pl(a[k])==pl(b[k])))]
    check(not lost, f"{eng} localStorage kept through the update (players, high scores, progress, problem letters, voice) lost/changed={lost}")
    names=await ev("[...document.querySelectorAll('#whoList button')].map(b=>b.textContent.trim())")
    up=await ev("JSON.parse(localStorage.getItem('lf-players')).every(p=>typeof p.u==='string'&&p.c>0)")
    check(up, f"{eng} existing players get their Family sync id + created date in place (same lf-players key)")
    await pg.click('#whoList button[data-id="p1"]'); await pg.wait_for_timeout(300)
    bst=await ev("JSON.stringify(best)"); vw=await ev("voiceWho")
    check("🙂Blakeli" in names and json.loads(bst).get("upper")==7 and json.loads(bst).get("num")==5 and vw=="dad", f"{eng} Blakeli's high scores show in the live app {bst}, voice {vw}")
    pb=await br.new_page() if False else await ctx.new_page(); await pb.goto(BASE+"beta/"); await pb.wait_for_timeout(2500)
    rb=await pb.evaluate("[navigator.serviceWorker.controller&&navigator.serviceWorker.controller.scriptURL, !!document.getElementById('goDrawNum')]")
    pp=await ctx.new_page(); await pp.goto(BASE+"parent/"); await pp.wait_for_timeout(1500)
    rp=await pp.evaluate("[!!document.getElementById('dash'), !document.getElementById('whoList'), navigator.serviceWorker.controller&&navigator.serviceWorker.controller.scriptURL]")
    check(rp[0] and rp[1], f"{eng} /parent/ opens the dashboard page through the live worker {rp}")
    check(rb[0] and rb[0].endswith("/beta/sw.js") and rb[1], f"{eng} the beta copy still works with its own worker {rb}")
    await br.close()
async def root(p,eng):
    br=await getattr(p,eng).launch(); ctx=await br.new_context(viewport={"width":1180,"height":820}); pg=await ctx.new_page(); ev=pg.evaluate
    net=[]; pg.on("response",lambda r: net.append((r.status,r.url))); pg.on("requestfailed",lambda r: net.append((-1,r.url)))
    errs=[]; pg.on("pageerror",lambda e: errs.append(str(e)))
    await pg.goto(BASE); await pg.wait_for_timeout(5000); await pg.reload(); await pg.wait_for_timeout(2500)
    sh=lambda n: pg.screenshot(path=SHOTS+f"v24-{TAG}-{eng}-{n}.png") if eng=="chromium" or n=="home" else asyncio.sleep(0)
    c=await ev("navigator.serviceWorker.controller&&navigator.serviceWorker.controller.scriptURL"); keys=await ev("caches.keys()")
    check(bool(c) and c.endswith("/letter-fun/sw.js") and not c.endswith("/beta/sw.js") and "letter-fun-v26" in keys, f"{eng} root worker {c}, caches {keys}")
    shell=await ev("caches.open('letter-fun-v26').then(c=>c.keys()).then(k=>k.map(r=>new URL(r.url).pathname))")
    check(any(k.endswith("/letter-fun/art.js") for k in shell) and not any("/beta/" in k for k in shell), f"{eng} live shell precache (art.js, no beta paths): {shell}")
    check(await ev("document.getElementById('who').classList.contains('on')"), f"{eng} root opens on Who's playing?"); await sh("whos-playing")
    await ev("localStorage.getItem('lf-players')") 
    await pg.click('#whoList button >> nth=0'); await pg.wait_for_timeout(400); await sh("home")
    await pg.click("#goNum"); await pg.wait_for_timeout(500)
    m=await ev("[document.getElementById('nums').classList.contains('on'), document.querySelectorAll('#nums svg.numg').length, !!document.getElementById('goDrawNum')]")
    check(m[0] and m[1]>=2 and m[2], f"{eng} Numbers 123 section with poster digits + Draw the Number {m}"); await sh("numbers-123")
    await pg.click("#goFindNum"); await pg.wait_for_timeout(2500)
    fn=await ev("[...document.querySelectorAll('#choices svg.numg')].map(s=>s.querySelectorAll('path').length)")
    check(len(fn)>=2 and all(x>=1 for x in fn), f"{eng} Find the Number tiles are poster digits {fn}"); await sh("find-the-number")
    await ev("""(()=>{ const b=[...document.querySelectorAll('#choices button.choice')].find(isRight); b.setAttribute('data-t','1'); })()""")
    await pg.click('#choices button[data-t="1"]'); await pg.wait_for_timeout(2500)
    await pg.click("#test .homeBtn"); await pg.wait_for_timeout(300); await pg.click("#goFingers"); await pg.wait_for_timeout(2500)
    h=await ev("[document.querySelectorAll('#hands [data-hand] path').length, +document.querySelector('#hands svg').dataset.total, document.querySelectorAll('#hands [data-up=\"1\"]').length]")
    check(h[0]==4 and h[1]==h[2], f"{eng} Count the Fingers: cartoon hands, fingers shown == total {h}"); await sh("fingers")
    await ev("""(()=>{ const b=[...document.querySelectorAll('#choices button.choice')].find(isRight); b.setAttribute('data-t','1'); })()""")
    await pg.click('#choices button[data-t="1"]'); await pg.wait_for_timeout(2500)
    await pg.click("#test .homeBtn"); await pg.wait_for_timeout(300); await pg.click("#goDrawNum"); await pg.wait_for_timeout(2500)
    d=await ev("[mode,dKind,dNum,(()=>{const g=guideC.getContext('2d').getImageData(0,0,guideC.width,guideC.height).data; let n=0; for(let i=3;i<g.length;i+=64) if(g[i]>0) n++; return n;})()]")
    check(d[0]=="draw" and d[1]=="num" and d[3]>200, f"{eng} Draw the Number game with the poster-digit guide {d}"); await sh("draw-number")
    await pg.click("#draw .homeBtn"); await pg.wait_for_timeout(300); await pg.click("#nums .homeBtn"); await pg.wait_for_timeout(300); await pg.click("#goABC"); await pg.wait_for_timeout(300); await sh("abc-menu")
    await pg.click("#goUpper"); await pg.wait_for_timeout(1500); await sh("upper-test")
    vl=await ev("vLog")
    base=BASE.split("//",1)[1].split("/",1)[1]
    mp3=[(s,u) for s,u in net if u.split("?")[0].endswith(".mp3")]
    yup=[(s,u) for s,u in mp3 if u.endswith("/letter-fun/voices/dad2/phrases/correct.mp3")]
    d2=[(s,u) for s,u in mp3 if "/letter-fun/voices/dad2/" in u]
    check("play:voices/dad2/phrases/correct.mp3" in vl and yup and all(s in (0,200,206) for s,_ in yup), f"{eng} Dad's 'Yup!' played from the root ({len(yup)} requests, statuses {sorted(set(s for s,_ in yup))})")
    check(any(x.startswith("play:voices/dad2/prompts/find_number_") for x in vl) and any(x=="play:voices/dad2/phrases/how_many_fingers.mp3" for x in vl) and len(d2)>=5 and all(s in (0,200,206) for s,_ in d2), f"{eng} dad2 voices play from the root: {len(d2)} dad2 responses, statuses {sorted(set(s for s,_ in d2))}")
    pl=sorted(set(x[5:] for x in vl if x.startswith("play:")))
    st=await ev("(u)=>Promise.all(u.map(x=>fetch(x).then(r=>r.status).catch(()=>-1)))",pl)
    check(pl and all(x==200 for x in st), f"{eng} every clip that played answers 200 from the root ({len(pl)} clips: {dict(zip(pl,st))})")
    bad=[(s,u) for s,u in net if s>=400 or s==-1]
    check(not bad, f"{eng} no 404s / failed requests ({len(net)} responses) {bad[:6]}")
    check(not [u for s,u in net if "/beta/" in u], f"{eng} the live app never loads anything from /beta/")
    check(not errs, f"{eng} no page errors {errs}")
    if eng=="chromium":
        await ctx.set_offline(True)
        try: await pg.reload()
        except Exception as e: await pg.goto(BASE)
        await pg.wait_for_timeout(1500)
        off=await ev("[!!window.LF_ART, document.getElementById('who').classList.contains('on'), fetch('voices/dad2/phrases/correct.mp3').then(r=>r.status).catch(e=>-1)]")
        off[2]=await ev("fetch('voices/dad2/phrases/correct.mp3').then(r=>r.status).catch(e=>-1)")
        check(off==[True,True,200], f"{eng} offline: live app + art + 'Yup!' clip from the cache {off}")
        await ctx.set_offline(False)
    await br.close()
async def main():
    async with async_playwright() as p:
        for e in ENG:
            print("=====",MODE,e,flush=True)
            try: await (upgrade if MODE=="upgrade" else root)(p,e)
            except Exception as x: check(False,f"{e} crashed: {x!r}"[:400])
    print("\nFAILS:",len(fails)); [print(" -",f) for f in fails]
asyncio.run(main())
