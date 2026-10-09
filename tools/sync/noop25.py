# v25: with sync-config.js = null (unconfigured) the app behaves exactly as before and talks to no backend
import asyncio,sys
from playwright.async_api import async_playwright
BASE=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8824/letter-fun/beta/"
fails=[]
def check(c,m):
    print(("  ok   " if c else "  FAIL ")+m,flush=True)
    if not c: fails.append(m)
async def main():
    async with async_playwright() as p:
        for eng in ["chromium","webkit"]:
            br=await getattr(p,eng).launch(); ctx=await br.new_context(viewport={"width":1180,"height":820}); pg=await ctx.new_page()
            ext=[]; pg.on("request",lambda r: ext.append(r.url) if "localhost" not in r.url and "127.0.0.1" not in r.url else None)
            errs=[]; pg.on("pageerror",lambda e: errs.append(str(e)))
            await pg.goto(BASE); await pg.wait_for_timeout(3500)
            check(await pg.evaluate("window.LF_SYNC_CONFIG===null && LFSync.ON===false && !syncOn()"), f"{eng}: sync is off (no config)")
            await pg.click('#whoList button[data-id="p1"]'); await pg.wait_for_timeout(300)
            await pg.evaluate("startGame('upper')"); await pg.wait_for_timeout(1500); await pg.evaluate("stopAll(); goHome()"); await pg.wait_for_timeout(1800)
            await pg.click("#gear"); await pg.wait_for_timeout(300)
            check(await pg.evaluate("[...document.querySelectorAll('#pBtns2 button')].map(b=>b.textContent).join('|')")=="👤 Players|📊 Stats|📈 Progress|☁️ Family sync", f"{eng}: Settings has ☁️ Family sync")
            await pg.screenshot(path=f"/workspace/letter-fun-shots/v25-settings-{eng}.png")
            await pg.click("#pSync"); await pg.wait_for_timeout(200)
            for k in "1256": await pg.click(f'#keypad button[data-k="{k}"]'); await pg.wait_for_timeout(60)
            await pg.wait_for_timeout(300)
            t=await pg.evaluate("[document.getElementById('sync').classList.contains('on'), document.getElementById('syState').textContent, getComputedStyle(document.getElementById('syLink')).display]")
            check(t[0] and "isn't switched on" in t[1] and t[2]=="none", f"{eng}: Family sync screen explains it isn't set up {t[1][:40]}")
            pl=await pg.evaluate("JSON.parse(localStorage.getItem('lf-players')).map(p=>[p.id,typeof p.u,p.u.length,p.c>0])")
            check(all(x[1]=="string" and x[2]>=16 and x[3] for x in pl), f"{eng}: players got a sync id + created date (same lf-players key) {pl}")
            await pg.goto(BASE+"parent/"); await pg.wait_for_timeout(800)
            check(await pg.evaluate("!document.getElementById('off').hidden && document.getElementById('dash').hidden"), f"{eng}: dashboard says sync isn't set up")
            if eng=="chromium": await pg.screenshot(path="/workspace/letter-fun-shots/v25-dashboard-not-set-up.png")
            check(not ext, f"{eng}: no requests leave the site {ext[:3]}")
            check(not errs, f"{eng}: no page errors {errs}")
            await br.close()
    print("\nFAILS:",len(fails)); [print(" -",f) for f in fails]
asyncio.run(main())
