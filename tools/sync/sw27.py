import asyncio,sys
from playwright.async_api import async_playwright
BASE=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8823/letter-fun/"
ENG=sys.argv[2].split(",") if len(sys.argv)>2 else ["chromium","webkit"]
fails=[]
def check(c,m):
    print(("  ok   " if c else "  FAIL ")+m,flush=True)
    if not c: fails.append(m)
async def run(p,eng):
    print("=====",eng,flush=True)
    br=await getattr(p,eng).launch(); ctx=await br.new_context(viewport={"width":1180,"height":820}); pg=await ctx.new_page(); ev=pg.evaluate
    await pg.goto(BASE); await pg.wait_for_timeout(1500)
    live=await ev("[!!document.getElementById('goABC'), document.documentElement.innerHTML.includes('voices/dad2')]")
    check(live==[True,True], f"{eng} live root is v24 (promoted) on voices/dad2: {live}")
    await pg.goto(BASE+"beta/"); await pg.wait_for_timeout(4000); await pg.reload(); await pg.wait_for_timeout(2500)
    c=await ev("navigator.serviceWorker.controller&&navigator.serviceWorker.controller.scriptURL")
    check(bool(c) and c.endswith("/beta/sw.js"), f"{eng} beta controlled by its own worker: {c}")
    keys=await ev("caches.keys()")
    check("letter-fun-beta-v27" in keys and not any(k.startswith("letter-fun-beta-v23") for k in keys), f"{eng} beta shell cache bumped to letter-fun-beta-v27: {keys}")
    shell=await ev("caches.open('letter-fun-beta-v27').then(c=>c.keys()).then(k=>k.map(r=>new URL(r.url).pathname))")
    check(all(any(k.endswith("/beta/"+f) for k in shell) for f in ["sync.js","sync-config.js","parent/index.html","parent/manifest.json"]), f"{eng} v25 shell precaches Family sync + the parent dashboard")
    check(any(k.endswith("/beta/art.js") for k in shell) and any(k.endswith("/beta/index.html") for k in shell), f"{eng} v24 shell precaches art.js (poster digits + hands): {shell}")
    want=["voices/dad2/numbers/4.mp3","voices/dad2/numbers/20.mp3","voices/dad2/phrases/how_many_fingers.mp3","voices/dad2/phrases/find_number.mp3","voices/dad2/prompts/find_number_13.mp3","voices/dad2/prompts/nope_an_8.mp3","voices/dad2/prompts/find_e.mp3","voices/dad2/sounds/e.mp3"]
    got=[]
    for i in range(30):
        ks=await ev("caches.open('letter-fun-audio-2').then(c=>c.keys()).then(k=>k.map(r=>new URL(r.url).pathname))")
        got=[w for w in want if any(k.endswith(w) for k in ks)]
        if len(got)==len(want) and sum('/dad2/' in k for k in ks)>=259: break
        await pg.wait_for_timeout(2000)
    n2=sum('/dad2/' in k for k in ks)
    check(len(got)==len(want) and n2>=259, f"{eng} worker cached dad2 clips incl. numbers/fingers/joined prompts ({n2} dad2 clips; missing {[w for w in want if w not in got]})")
    check(any(k.endswith("/letter-fun/beta/voices/dad2/phrases/correct.mp3") for k in ks), f"{eng} Dad's 'Yup!' (beta/voices/dad2/phrases/correct.mp3) is in the audio cache")
    r=await ev("fetch('../voices/dad2/numbers/7.mp3').then(r=>[r.status,r.headers.get('content-type')])")
    check(r[0]==200, f"{eng} dad2 clip served through the beta worker: {r}")
    if eng=="webkit":
        print("  note: offline check skipped on webkit (Playwright WebKit can't navigate with set_offline)"); await br.close(); return
    # offline: reload with the network off - the app, the poster digits and the hands still come up
    await ctx.set_offline(True)
    try: await pg.reload()
    except Exception as e:
        print("  note: offline reload raised in",eng,str(e)[:120]); await pg.goto(BASE+"beta/")
    await pg.wait_for_timeout(1500)
    off=await ev("[!!window.LF_ART, typeof numSvg==='function'&&!!numSvg(17)]")
    await ev("setPlayer('p1'); startGame('fingers'); quiet()"); await pg.wait_for_timeout(300)
    off2=await ev("[document.querySelectorAll('#choices svg.numg').length, document.querySelectorAll('#hands [data-hand] path').length]")
    await ev("startDraw('num'); quiet()"); await pg.wait_for_timeout(300)
    off3=await ev("(()=>{const d=guideC.getContext('2d').getImageData(0,0,guideC.width,guideC.height).data; let n=0; for(let i=3;i<d.length;i+=64) if(d[i]>0) n++; return n;})()")
    yup=await ev("fetch('voices/dad2/phrases/correct.mp3').then(r=>r.arrayBuffer().then(b=>[r.status,b.byteLength])).catch(e=>String(e))")
    check(isinstance(yup,list) and yup[0]==200 and yup[1]>3000, f"{eng} offline: 'Yup!' clip served from the cache {yup}")
    check(off==[True,True] and off2==[10,4] and off3>100, f"{eng} offline: app + art load from the worker cache {off} {off2} {off3}")
    await pg.screenshot(path=f"/workspace/letter-fun-shots/v24-offline-{eng}-draw-number.png")
    await pg.goto(BASE+"beta/parent/"); await pg.wait_for_timeout(800)
    check(await ev("!!document.getElementById('dash')&&!document.getElementById('whoList')"), f"{eng} offline: /beta/parent/ opens the dashboard page (not the app)")
    await ctx.set_offline(False)
    await br.close()
async def main():
    async with async_playwright() as p:
        for e in ENG: await run(p,e)
    print("\nFAILS:",len(fails)); [print(" -",f) for f in fails]
asyncio.run(main())
