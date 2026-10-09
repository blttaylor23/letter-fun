# v25 Family sync: two devices (separate browser contexts) + the parent dashboard, against the local Firebase emulators.
# Usage: sync25.py [BASE] [engine]   BASE = the app folder, e.g. http://localhost:8824/letter-fun/beta/
import asyncio,sys,json,os,time
from playwright.async_api import async_playwright
BASE=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8824/letter-fun/beta/"
ENG=sys.argv[2] if len(sys.argv)>2 else "chromium"
SHOTS="/workspace/letter-fun-shots/"; TAG=sys.argv[3] if len(sys.argv)>3 else "v25"
FAM="famtest-"+str(int(time.time()))
CFG="window.LF_SYNC_CONFIG="+json.dumps({"apiKey":"demo-key","db":"http://127.0.0.1:9000","dbq":"ns=demo-letterfun-default-rtdb","fam":FAM,
  "authBase":"http://127.0.0.1:9099/identitytoolkit.googleapis.com","tokenBase":"http://127.0.0.1:9099/securetoken.googleapis.com"})+";"
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
        A=await device(br,"device A (iPhone)"); B=await device(br,"device B (iPad)",820,1180)
        # ---- before linking: everything stays local, no requests to the backend
        await pick(A,"p1"); await play(A,"upper",3,25); await play(A,"num",2,10)
        check(await A.evaluate("syncOn()&&!syncLinked()"), "A: sync configured but not linked -> nothing is sent")
        r=await link(A,True); check(r[0] and "Linked" in r[1], f"A creates the family password + links: {r[1]!r}")
        await A.screenshot(path=SHOTS+f"{TAG}-family-sync-linked.png")
        await pick(B,"p1"); await play(B,"upper",5,40); await play(B,"fingers",4,15)
        await B.evaluate("stopAll(); openWho()"); await B.wait_for_timeout(200)
        await tap(B,"#whoAdd",200); await B.fill("#whoNew","Max"); await tap(B,"#whoOk",300)
        mx=await B.evaluate("players.find(p=>p.name==='Max').id"); await pick(B,mx); await play(B,"lower",2,12); await play(B,"num",3,8)
        r=await link(B,False); check(r[0], f"B links with the same password: {r[1]!r}")
        for pg in (A,B): await freeze(pg)
        await sync(A); await sync(B); await sync(A)
        names=await A.evaluate("players.map(p=>p.name)")
        check("Max" in names, f"A: Max (added on B) appears as a profile on A: {names}")
        await A.evaluate("stopAll(); openWho()"); await A.wait_for_timeout(200)
        check("Max" in await A.evaluate("[...document.querySelectorAll('#whoList button')].map(b=>b.textContent).join()"), "A: Max is in Who's playing?")
        await A.screenshot(path=SHOTS+f"{TAG}-device-A-whos-playing.png")
        sa=await state(A,"p1"); sb=await state(B,"p1")
        check(sa==sb, f"Blakeli identical on A and B (high scores, hours, right/wrong): A={sa['best']} {sa['total']//60000} min, B={sb['best']} {sb['total']//60000} min")
        check(sa["best"]["upper"]==5 and sa["best"]["num"]==2 and sa["best"]["fingers"]==4, f"high scores = max per game across devices {sa['best']}")
        check(abs(sa["total"]-(25+10+40+15)*60000)<120000, f"Blakeli's hours = A + B, no double counting ({sa['total']/60000:.1f} min, expected ~90)")
        tot=sum(v[0] for v in sa["prog"].values()), sum(v[1] for v in sa["prog"].values())
        check(tot[0]>=14 and tot[1]>=4, f"right/wrong counts summed across devices {tot}")
        mA=await state(A,await A.evaluate("players.find(p=>p.name==='Max').id")); mB=await state(B,mx)
        check(mA==mB and mA["best"]["lower"]==2, f"Max identical on A and B {mA['best']} {mA['total']//60000} min")
        # sync again: nothing doubles
        await sync(A); await sync(B); await sync(A); sa2=await state(A,"p1")
        check(sa2==sa, "syncing again changes nothing (no double counting)")
        # ---- Stats + Progress screens show the merged numbers
        await A.evaluate("openStats()"); await A.wait_for_timeout(200)
        st=await A.evaluate("[...document.querySelectorAll('#stList .stCard')].map(c=>[c.querySelector('b').textContent,+c.dataset.total])")
        check(dict(st).get("Blakeli")==sa["total"], f"A: Stats shows Blakeli's combined time {st}")
        await A.screenshot(path=SHOTS+f"{TAG}-device-A-stats.png")
        # ---- the dashboard (Bobby's phone: a third context, linked with the password on the page itself)
        D=await device(br,"parent phone",390,844)
        await D.goto(BASE+"parent/"); await D.wait_for_timeout(800)
        check(await D.evaluate("!document.getElementById('setup').hidden"), "dashboard asks for the family password on a new device")
        await D.fill("#pw","wrong-password"); await tap(D,"#go",800)
        check("not the family" in await D.evaluate("document.getElementById('msg').textContent"), "dashboard: wrong password refused")
        await D.fill("#pw",PW); await tap(D,"#go",300); await D.wait_for_function("window.__dash",timeout=10000)
        d=await D.evaluate("({tot:__dash.total.total, pl:__dash.players.map(p=>[p.name,p.devices,p.time.total,p.alive,p.best]), hm:document.getElementById('totalHM').textContent, cards:[...document.querySelectorAll('.pl')].map(c=>c.dataset.name)})")
        exp=(25+10+40+15+12+8)*60000
        check(abs(d["tot"]-exp)<180000, f"dashboard total = everyone on every device ({d['tot']/60000:.1f} min ~ {exp/60000}) shown as {d['hm']}")
        bl=[x for x in d["pl"] if x[0]=="Blakeli"][0]
        check(bl[1]==2 and bl[2]==sa["total"] and bl[4].get("upper")==5, f"dashboard: Blakeli merged across 2 devices, same hours + high scores as the app {bl}")
        check([x for x in d["pl"] if x[0]=="Max"][0][1]==1 and "Little Bobby" in d["cards"], f"dashboard lists every player: {d['cards']}")
        await D.screenshot(path=SHOTS+f"{TAG}-dashboard.png"); await D.screenshot(path=SHOTS+f"{TAG}-dashboard-full.png",full_page=True)
        await D.evaluate("document.querySelectorAll('details').forEach(x=>x.open=true)"); await D.screenshot(path=SHOTS+f"{TAG}-dashboard-details.png",full_page=True)
        # ---- offline queueing on B
        await B.ctx.set_offline(True); await pick(B,"p1") if await B.evaluate("mode==='who'") else None
        await B.evaluate("setPlayer('p1')"); await play(B,"upper",7,20); await freeze(B)
        ok=await sync(B); st=await B.evaluate("lsGet(SYNC_STATE,{})")
        check(not ok and st.get("pending") and await B.evaluate("mode")!="", f"B offline: the sync fails quietly, marked pending, play goes on ({st.get('err')})")
        n0=await B.evaluate("window.__syncCount"); await B.ctx.set_offline(False)
        await B.evaluate("window.dispatchEvent(new Event('online'))")
        await B.wait_for_function(f"window.__syncCount>{n0}&&!(lsGet(SYNC_STATE,{{}})||{{}}).pending",timeout=15000)
        await sync(A); sa3=await state(A,"p1"); sb3=await state(B,"p1")
        check(sa3==sb3 and sa3["best"]["upper"]==7 and abs(sa3["total"]-sa["total"]-20*60000)<60000, f"back online: B's queued play reaches A (upper ⭐ {sa3['best']['upper']}, +{(sa3['total']-sa['total'])/60000:.0f} min)")
        # ---- delete Max on A (code 1256) -> gone on B, still counted in the family total
        await A.evaluate("stopAll(); openSettings()"); await tap(A,"#pPlayers",300)
        await A.click('#plList .hsRow:has-text("Max") button.rm'); await code(A)
        check("Max" not in await A.evaluate("players.map(p=>p.name)"), "A: Max deleted with the code")
        await A.wait_for_timeout(2500); await sync(A); await sync(B)
        check("Max" not in await B.evaluate("players.map(p=>p.name)"), f"B: Max is gone after sync too (soft delete) {await B.evaluate('players.map(p=>p.name)')}")
        await sync(A); check("Max" not in await A.evaluate("players.map(p=>p.name)"), "A: Max doesn't come back")
        await tap(D,"#refresh",300); await D.wait_for_timeout(1500)
        d2=await D.evaluate("({tot:__dash.total.total, max:__dash.players.filter(p=>p.name==='Max').map(p=>[p.alive,p.time.total])})")
        check(d2["max"] and d2["max"][0][0]==False and d2["max"][0][1]>=20*60000 and d2["tot"]>=d["tot"], f"dashboard: Max shown as deleted, hours kept in the total {d2}")
        await D.screenshot(path=SHOTS+f"{TAG}-dashboard-after-delete.png",full_page=True)
        # ---- reset on A reaches B
        await A.evaluate("setPlayer('p1'); resetBest('p1',['upper'])"); await sync(A); await sync(B)
        rb=await B.evaluate("[loadBest('p1').upper, best.upper, curPlayer]"); ra=await A.evaluate("loadBest('p1').upper")
        check(rb[0]==0 and ra==0, f"high-score reset on A reaches B (A {ra}, B {rb})")
        # ---- re-adding a deleted name later brings it back everywhere
        await B.evaluate("newPlayer('Max')"); await B.wait_for_timeout(200); await sync(B); await sync(A)
        check("Max" in await A.evaluate("players.map(p=>p.name)"), "re-adding Max later (on B) brings him back on A")
        # ---- the in-app button opens the dashboard; back returns to the app
        await A.evaluate("stopAll(); openSettings()"); await tap(A,"#pSync",300); await code(A)
        await A.screenshot(path=SHOTS+f"{TAG}-family-sync-screen.png")
        await A.click("#syParent"); await A.wait_for_url("**/parent/",timeout=8000); await A.wait_for_function("window.__dash",timeout=10000)
        check(await A.evaluate("!!window.__dash && document.getElementById('setup').hidden"), "Parent dashboard button opens the dashboard (no second password on a linked device)")
        await A.click("a.back"); await A.wait_for_timeout(800)
        check(await A.evaluate("typeof openWho==='function' && document.getElementById('who').classList.contains('on')"), "◀ App goes back to the app")
        for pg in (A,B,D): check(not pg.errs, f"{pg.nm}: no page errors {pg.errs}")
        await br.close()
    print("\nFAILS:",len(fails)); [print(" -",f) for f in fails]
asyncio.run(main())
