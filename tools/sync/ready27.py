# v26: with the real backend configured: Family sync screen says ready, dashboard shows the set-up state, no console errors / 404s.
# Never links a device, never creates the family password. Usage: ready26.py BASE (e.g. https://blttaylor23.github.io/letter-fun/ or http://localhost:8824/letter-fun/beta/) engines tag
import asyncio,sys
from playwright.async_api import async_playwright
BASE=sys.argv[1]; ENG=(sys.argv[2] if len(sys.argv)>2 else "chromium,webkit").split(","); TAG=sys.argv[3] if len(sys.argv)>3 else "v26"
SHOTS="/workspace/letter-fun-shots/"; fails=[]
def check(c,m):
    print(("  ok   " if c else "  FAIL ")+m,flush=True)
    if not c: fails.append(m)
async def main():
    async with async_playwright() as p:
        for eng in ENG:
            br=await getattr(p,eng).launch(); ctx=await br.new_context(viewport={"width":1180,"height":820}); pg=await ctx.new_page(); ev=pg.evaluate
            net=[]; cons=[]; errs=[]
            pg.on("response",lambda r: net.append((r.status,r.request.method,r.url)))
            pg.on("requestfailed",lambda r: net.append((-1,r.method,r.url)))
            pg.on("console",lambda m: cons.append(m.text) if m.type=="error" else None); pg.on("pageerror",lambda e: errs.append(str(e)))
            await pg.goto(BASE); await pg.wait_for_timeout(4500); await pg.reload(); await pg.wait_for_timeout(2500)
            check(await ev("[LFSync.ON, !!LF_SYNC_CONFIG.apiKey, /firebaseio\\.com/.test(LF_SYNC_CONFIG.db), /^fam-/.test(LF_SYNC_CONFIG.fam), LFSync.status().linked]")==[True,True,True,True,False], f"{eng}: sync-config.js loaded (apiKey/db/fam present), sync ON, this device not linked")
            check(await ev("navigator.serviceWorker.controller&&/sw\\.js$/.test(navigator.serviceWorker.controller.scriptURL)") , f"{eng}: service worker in control")
            keys=await ev("caches.keys()"); check(any(k.endswith("-v27") and k.startswith("letter-fun") for k in keys), f"{eng}: v27 shell cache {keys}")
            await pg.click('#whoList button[data-id="p1"]'); await pg.wait_for_timeout(300)
            await pg.click("#gear"); await pg.wait_for_timeout(300); await pg.click("#pSync"); await pg.wait_for_timeout(200)
            for k in "1256": await pg.click(f'#keypad button[data-k="{k}"]'); await pg.wait_for_timeout(60)
            await pg.wait_for_function("syHas!==null",timeout=15000)
            t=await ev("[document.getElementById('syState').textContent, document.getElementById('syGo').textContent, getComputedStyle(document.getElementById('syLink')).display, !document.getElementById('syPw2').classList.contains('off')]")
            created=("Type the family sync password" in t[0] and t[1]=="Link this device" and not t[3])
            check((("Make up a family sync password" in t[0] and t[1]=="Create + link" and t[3]) or created) and t[2]!="none", f"{eng}: Family sync screen is ready: asks Bobby to create the family password {t[0][:60]!r} / {t[1]!r}")
            await pg.screenshot(path=SHOTS+f"{TAG}-family-sync-ready-{eng}.png")
            await pg.goto(BASE+"parent/"); await pg.wait_for_timeout(2500)
            d=await ev("[!document.getElementById('setup').hidden, document.getElementById('dash').hidden, document.getElementById('off').hidden, document.getElementById('setupText').textContent, document.getElementById('go').textContent]")
            check(d[0] and d[1] and d[2] and ("Make up" in d[3] or "Type the family sync password" in d[3]), f"{eng}: dashboard shows the set-up state (create the family password) {d[3][:50]!r} / {d[4]!r}")
            await pg.screenshot(path=SHOTS+f"{TAG}-dashboard-setup-{eng}.png")
            bad=[(s,u.split("?")[0][-60:]) for s,m,u in net if (s>=400 or s==-1)]
            check(not bad, f"{eng}: no 404s / failed requests ({len(net)} requests) {bad[:5]}")
            wr=[(m,u.split("?")[0][-50:]) for s,m,u in net if "firebaseio" in u and m!="GET"]
            check(not wr, f"{eng}: nothing written to the backend (read-only look) {wr}")
            check(not cons and not errs, f"{eng}: no console errors / page errors {cons[:3]} {errs[:3]}")
            await br.close()
    print("\nFAILS:",len(fails)); [print(" -",f) for f in fails]
asyncio.run(main())
