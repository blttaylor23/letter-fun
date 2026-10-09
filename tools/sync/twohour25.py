# v25 Family sync: two devices (separate browser contexts) + the parent dashboard, against the local Firebase emulators.
# Usage: sync25.py [BASE] [engine]   BASE = the app folder, e.g. http://localhost:8824/letter-fun/beta/
import asyncio,sys,json,os,time
from playwright.async_api import async_playwright
BASE=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8824/letter-fun/beta/"
ENG=sys.argv[2] if len(sys.argv)>2 else "chromium"
SHOTS="/workspace/letter-fun-shots/"; TAG=sys.argv[3] if len(sys.argv)>3 else "v25"
FAM="famtest-"+str(int(time.time()))
_E={"apiKey":"demo-key","db":"http://127.0.0.1:9000","dbq":"ns=demo-letterfun-default-rtdb","fam":FAM,
  "authBase":"http://127.0.0.1:9099/identitytoolkit.googleapis.com","tokenBase":"http://127.0.0.1:9099/securetoken.googleapis.com"}
if os.environ.get("LF_REAL"):   # the REAL Firebase backend with a throwaway family id (key + db read from the repo's sync-config.js, never printed)
    import re as _re
    _t=open("/workspace/letter-fun/sync-config.js").read(); _g=lambda k:_re.search(k+r':"([^"]+)"',_t).group(1)
    FAM="selftest-"+str(int(time.time())); _E={"apiKey":_g("apiKey"),"db":_g("db"),"fam":FAM}
    open("/tmp/lf_throwaway_fam","a").write(FAM+"\n")
CFG="window.LF_SYNC_CONFIG="+json.dumps(_E)+";"
PW="tiger-moon-42"
fails=[]
def check(c,m):
    print(("  ok   " if c else "  FAIL ")+m,flush=True)
    if not c: fails.append(m)
async def device(br,name,vw=1180,vh=820):
    ctx=await br.new_context(viewport={"width":vw,"height":vh},service_workers="block")
    async def cfg(route): await route.fulfill(body=CFG,content_type="application/javascript")
    await ctx.route("**/sync-config.js",cfg)
    pg=await ctx.new_page(); errs=[]; pg.on("pageerror",lambda e: errs.append(str(e))); pg.errs=errs; pg.ctx=ctx; pg.nm=name
    await pg.goto(BASE); await pg.wait_for_timeout(600); return pg
async def tap(pg,sel,wait=250): await pg.click(sel); await pg.wait_for_timeout(wait)
async def code(pg):
    for k in "1256": await tap(pg,f'#keypad button[data-k="{k}"]',60)
    await pg.wait_for_timeout(300)
async def pick(pg,pid): await tap(pg,f'#whoList button[data-id="{pid}"]',300)
async def play(pg,game,n,minutes):
    """n correct answers in a game (real taps) + `minutes` of play time added to today's counters (simulated time)"""
    await pg.evaluate(f"(()=>{{ stopAll(); startGame('{game}'); }})()"); await pg.wait_for_timeout(300)
    for i in range(n):
        await pg.wait_for_function("mode==='test'&&!tBusy",timeout=12000)
        await pg.evaluate("(()=>{ const b=[...document.querySelectorAll('#choices button.choice')].find(isRight); b.setAttribute('data-t','1'); })()")
        await pg.click('#choices button[data-t="1"]'); await pg.wait_for_timeout(150)
        await pg.wait_for_function("!tBusy",timeout=12000)
    await pg.evaluate("(()=>{ const b=[...document.querySelectorAll('#choices button.choice')].find(b=>!isRight(b)); b.setAttribute('data-t','1'); })()")
    await pg.click('#choices button[data-t="1"]'); await pg.wait_for_timeout(200); await pg.wait_for_function("!tBusy",timeout=12000)
    await pg.evaluate(f"(()=>{{ const k=dayKey(Date.now()), ms={minutes}*60000; timeData.total+=ms; timeData.days[k]=(timeData.days[k]||0)+ms; timeData.games[game]=(timeData.games[game]||0)+ms; timeData.last=Date.now(); timeDirty=1; flushTime(); }})()")
    await tap(pg,"#test .homeBtn",300)
async def freeze(pg): await pg.evaluate("lastAct=0; safe(flushTime)")   # idle: the clock stops (so both devices can be compared)
async def sync(pg): return await pg.evaluate("__sync.now()")
async def link(pg,create):
    await pg.evaluate("stopAll(); openSettings()"); await pg.wait_for_timeout(200)
    await tap(pg,"#pSync",300); await code(pg)
    check(await pg.evaluate("document.getElementById('sync').classList.contains('on')"), f"{pg.nm}: Settings ▸ ☁️ Family sync opens after the grown-up code 1256")
    await pg.wait_for_function("syHas!==null",timeout=8000)
    await pg.fill("#syPw",PW)
    if create: await pg.fill("#syPw2",PW)
    await tap(pg,"#syGo",300); await pg.wait_for_function("syncLinked()&&(lsGet(SYNC_STATE,{})||{}).ok>0",timeout=15000)
    return await pg.evaluate("[syncLinked(), document.getElementById('syMsg').textContent, document.getElementById('syState').textContent]")
async def state(pg,pid):
    return await pg.evaluate(f"""(()=>{{ const b=loadBest('{pid}'), t=statTime('{pid}'), it=progAll('{pid}').items, o={{}};
      for(const k of Object.keys(it).sort()) o[k]=[it[k].r,it[k].w]; return {{best:b,total:t.total,today:t.days[dayKey(Date.now())]||0,prog:o}}; }})()""")
async def main():
    async with async_playwright() as p:
        br=await getattr(p,ENG).launch()
        A=await device(br,"device A",1180,820); B=await device(br,"device B",820,1180)
        for pg in (A,B): await pick(pg,"p2")   # Little Bobby on both
        await play(A,"num",3,60); await play(B,"upper",2,60)
        for pg in (A,B): await freeze(pg)
        await link(A,True); await link(B,False)
        await sync(A); await sync(B); await sync(A)
        for pg in (A,B): await freeze(pg)
        sa=await state(A,"p2"); sb=await state(B,"p2")
        check(abs(sa["total"]-120*60000)<60000 and sa["total"]==sb["total"], f"1 h on A + 1 h on B = 2 h on BOTH devices: A {sa['total']/3600000:.2f} h, B {sb['total']/3600000:.2f} h")
        check(sa==sb and sa["best"]["num"]==3 and sa["best"]["upper"]==2, f"Little Bobby's high scores (max per game) + right/wrong identical on both {sa['best']}")
        for i in range(3): await sync(A); await sync(B)
        sa2=await state(A,"p2"); sb2=await state(B,"p2")
        check(sa2==sa and sb2==sb, "six more syncs: still exactly 2 h (never double counts)")
        # more play on A: B sees only the new delta
        await A.evaluate("setPlayer('p2')"); await play(A,"fingers",1,30); await freeze(A); await sync(A); await sync(B)
        sb3=await state(B,"p2"); check(abs(sb3["total"]-150*60000)<60000, f"+30 min on A -> B shows 2.5 h ({sb3['total']/3600000:.2f} h)")
        # the app restarts on A (reload): local counters + cloud give the same 2.5 h, nothing re-added
        await A.reload(); await A.wait_for_timeout(1200); await A.evaluate("setPlayer('p2')"); await sync(A); await sync(B)
        sa4=await state(A,"p2"); sb4=await state(B,"p2"); check(sa4["total"]==sb4["total"] and abs(sa4["total"]-150*60000)<60000, f"after reopening the app on A: still {sa4['total']/3600000:.2f} h on both")
        await A.evaluate("openStats()"); await A.wait_for_timeout(300); await A.screenshot(path=SHOTS+f"{TAG}-two-devices-2h-A-stats.png")
        await B.evaluate("openStats()"); await B.wait_for_timeout(300); await B.screenshot(path=SHOTS+f"{TAG}-two-devices-2h-B-stats.png")
        for pg in (A,B): check(not pg.errs, f"{pg.nm}: no page errors {pg.errs}")
        await br.close()
    print("\nFAILS:",len(fails)); [print(" -",f) for f in fails]
asyncio.run(main())
