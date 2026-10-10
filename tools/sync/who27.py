# v27: the "Who's playing?" screen scrolls (touch swipe / wheel), nothing clipped, Add player reachable, other screens unchanged.
import asyncio,sys,json
from playwright.async_api import async_playwright
BASE=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8824/letter-fun/"
ENGS=(sys.argv[2] if len(sys.argv)>2 else "chromium,webkit").split(",")
TAG=sys.argv[3] if len(sys.argv)>3 else "v27"
SHOTS="/workspace/letter-fun-shots/"; fails=[]
def check(c,m):
    print(("  ok   " if c else "  FAIL ")+m,flush=True)
    if not c: fails.append(m)
NAMES=["Blakeli","Little Bobby","Ava","Max","Zoe","Leo","Mia","Sam","Eli","Ivy","Noah","Ruby"]
def players(n): return json.dumps([{"id":"p%d"%(i+1),"name":NAMES[i],"u":"u%02d"%i+"x"*10,"c":1700000000000} for i in range(n)])
VPS=[("iPhone portrait",390,844),("small phone portrait",360,640),("iPhone landscape",844,390),("small landscape",667,375)]
async def swipe(cdp,x,y0,y1,steps=12):
    await cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":x,"y":y0}]})
    for i in range(1,steps+1):
        await cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":x,"y":y0+(y1-y0)*i/steps}]}); await asyncio.sleep(0.016)
    await cdp.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]})
async def metrics(pg):
    return await pg.evaluate("""(()=>{ const w=document.getElementById('who'), r=w.getBoundingClientRect(), vh=innerHeight, h=w.querySelector('h1').getBoundingClientRect(), bs=[...document.querySelectorAll('#whoList button')].map(b=>b.getBoundingClientRect()), a=document.getElementById('whoAdd'), ar=a.getBoundingClientRect();
      return {sh:w.scrollHeight,ch:w.clientHeight,st:w.scrollTop,vh,top:r.top,bottom:r.bottom,h1top:h.top,h1bot:h.bottom,first:bs[0]&&bs[0].top,last:bs.length&&bs[bs.length-1].bottom,lastLeft:bs.length&&bs[bs.length-1].left,lastRight:bs.length&&bs[bs.length-1].right,n:bs.length,add:getComputedStyle(a).display!=='none',addTop:ar.top,addBot:ar.bottom,vw:innerWidth,docSH:document.documentElement.scrollHeight}; })()""")
async def run(p,eng):
    br=await getattr(p,eng).launch()
    for name,vw,vh in VPS:
        tag=f"{eng} {name} {vw}x{vh}"; slug=name.replace(" ","-")
        ctx=await br.new_context(viewport={"width":vw,"height":vh},has_touch=True,is_mobile=(eng=="chromium"),device_scale_factor=2,service_workers="block")
        pg=await ctx.new_page(); errs=[]; pg.on("pageerror",lambda e: errs.append(str(e)))
        for n in (12,7,3):
            await pg.goto(BASE); await pg.evaluate(f"localStorage.setItem('lf-players',{json.dumps(players(n))}); localStorage.removeItem('lf-player')")
            await pg.reload(); await pg.wait_for_timeout(500)
            m=await metrics(pg); t=f"{tag} {n} players"
            check(m["n"]==n and m["top"]==0 and abs(m["bottom"]-m["vh"])<=1, f"{t}: the screen fills the viewport ({m['top']},{m['bottom']} of {m['vh']})")
            check(m["docSH"]<=m["vh"]+1, f"{t}: the page itself doesn't scroll (only the picker does)")
            if n==12:
                check(m["sh"]>m["ch"]+20, f"{t}: content taller than the screen ({m['sh']} > {m['ch']}), so it must scroll")
                check(m["h1top"]>=0 and m["first"]>=m["h1bot"], f"{t}: top not clipped at scrollTop 0 (heading top {m['h1top']:.0f})")
                await pg.screenshot(path=SHOTS+f"{TAG}-whos-playing-{eng}-{slug}-12-top.png")
                # a real swipe up on touch devices (chromium); mouse wheel everywhere
                if eng=="chromium":
                    cdp=await ctx.new_cdp_session(pg)
                    await swipe(cdp,vw//2,int(vh*0.8),int(vh*0.3))
                    await pg.wait_for_timeout(500); s1=(await metrics(pg))["st"]
                    check(s1>40, f"{t}: touch swipe up scrolls the list (scrollTop {s1:.0f})")
                    check(await pg.evaluate("document.getElementById('who').classList.contains('on')"), f"{t}: a swipe doesn't pick a player")
                    await swipe(cdp,vw//2,int(vh*0.3),int(vh*0.7))
                    await pg.wait_for_timeout(500); s2=(await metrics(pg))["st"]
                    check(s2<s1-20, f"{t}: swipe down scrolls back up ({s1:.0f} -> {s2:.0f})")
                await pg.evaluate("document.getElementById('who').scrollTop=0"); await pg.mouse.move(vw//2,vh//2); await pg.mouse.wheel(0,400); await pg.wait_for_timeout(400)
                check((await metrics(pg))["st"]>100, f"{t}: mouse wheel scrolls")
                await pg.evaluate("document.getElementById('who').scrollTop=1e6"); await pg.wait_for_timeout(300); m=await metrics(pg)
                check(m["last"]<=m["vh"]+0.5 and m["last"]>m["vh"]-60 and m["lastLeft"]>=0 and m["lastRight"]<=m["vw"]+0.5, f"{t}: last player fully reachable at the bottom ({m['last']:.0f} of {m['vh']}), not clipped")
                await pg.screenshot(path=SHOTS+f"{TAG}-whos-playing-{eng}-{slug}-12-bottom.png")
                # tapping a player after scrolling still works
                await pg.evaluate("document.getElementById('whoList').lastElementChild.setAttribute('data-t','1')"); await pg.tap('#whoList button[data-t="1"]'); await pg.wait_for_timeout(400)
                check(await pg.evaluate("document.getElementById('home').classList.contains('on')&&curPlayer==='p12'"), f"{t}: tapping the last player (after scrolling) starts as them")
            elif n==7:
                await pg.evaluate("document.getElementById('who').scrollTop=1e6"); await pg.wait_for_timeout(300); m=await metrics(pg)
                check(m["add"] and m["addTop"]>=0 and m["addBot"]<=m["vh"]+0.5, f"{t}: ＋ Add player reachable at the bottom ({m['addTop']:.0f}-{m['addBot']:.0f} of {m['vh']})")
                await pg.screenshot(path=SHOTS+f"{TAG}-whos-playing-{eng}-{slug}-7-add.png")
                await pg.tap("#whoAdd"); await pg.wait_for_timeout(400)
                fr=await pg.evaluate("(()=>{const r=document.getElementById('whoForm').getBoundingClientRect(); return [document.getElementById('whoForm').classList.contains('on'), r.top>=0, r.bottom<=innerHeight+0.5]})()")
                check(fr==[True,True,True], f"{tag}: the name box opens fully on screen {fr}")
                await pg.fill("#whoNew","Nova"); await pg.tap("#whoOk"); await pg.wait_for_timeout(400)
                check(await pg.evaluate("players.some(p=>p.name==='Nova')&&document.getElementById('who').classList.contains('on')"), f"{tag}: adding a player from the scrolled screen works")
            else:
                await pg.evaluate("document.getElementById('who').scrollTop=1e6"); await pg.wait_for_timeout(250); m2=await metrics(pg)
                check(m["h1top"]>=0 and (m["sh"]<=m["ch"]+1 or (m2["add"] and m2["addBot"]<=m2["vh"]+0.5)), f"{t}: top not clipped; fits ({m['sh']<=m['ch']+1}) or scrolls to the Add button")
                await pg.screenshot(path=SHOTS+f"{TAG}-whos-playing-{eng}-{slug}-3.png")
        # other screens keep their current behaviour
        await pg.goto(BASE); await pg.evaluate("localStorage.removeItem('lf-players'); localStorage.removeItem('lf-player')"); await pg.reload(); await pg.wait_for_timeout(400)
        await pg.tap('#whoList button[data-id="p1"]'); await pg.wait_for_timeout(300)
        ov=await pg.evaluate("['home','abc','nums','test','draw'].map(id=>{ const e=document.getElementById(id); return [id,getComputedStyle(e).overflowY,getComputedStyle(e).touchAction]; })")
        check(all(o[1] in("visible","hidden") for o in ov), f"{tag}: home/menus/test/draw screens don't scroll {ov}")
        await pg.evaluate("startDraw('letter'); quiet()"); await pg.wait_for_timeout(500)
        ds=await pg.evaluate("[getComputedStyle(document.getElementById('dStage')).touchAction, getComputedStyle(inkC).touchAction, document.getElementById('who').classList.contains('on')]")
        check(ds==["none","none",False], f"{tag}: draw canvas still touch-action:none {ds}")
        if eng=="chromium":
            cdp=await ctx.new_cdp_session(pg); y0=await pg.evaluate("scrollY")
            await swipe(cdp,vw//2,int(vh*0.6),int(vh*0.3)); await pg.wait_for_timeout(400)
            check((await pg.evaluate("[scrollY, document.documentElement.scrollTop]"))==[y0,0], f"{tag}: dragging on the draw canvas doesn't scroll the page (it draws)")
        check(not errs, f"{tag}: no page errors {errs}")
        await ctx.close()
    await br.close()
async def main():
    async with async_playwright() as p:
        for e in ENGS: print("=====",e,flush=True); await run(p,e)
    print("\nFAILS:",len(fails)); [print(" -",f) for f in fails]
asyncio.run(main())
