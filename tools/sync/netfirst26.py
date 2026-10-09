import asyncio,sys,os
from playwright.async_api import async_playwright
fails=[]
async def main():
    async with async_playwright() as p:
        br=await p.chromium.launch(); ctx=await br.new_context(); pg=await ctx.new_page()
        base="http://localhost:8830/letter-fun/"
        os.system("ln -sfn /workspace/letter-fun /tmp/srvup/letter-fun")
        await pg.goto(base); await pg.wait_for_timeout(4000); await pg.reload(); await pg.wait_for_timeout(1500)
        a=await pg.evaluate("fetch('sync-config.js').then(r=>r.text()).then(t=>/fam-/.test(t))")
        # change the config on the server: a normal (non-reload) fetch through the worker must see it at once
        os.system("rm -rf /tmp/cfgtest && mkdir /tmp/cfgtest && cp -r /workspace/letter-fun/. /tmp/cfgtest/ 2>/dev/null; echo 'window.LF_SYNC_CONFIG=null;//changed' > /tmp/cfgtest/sync-config.js; ln -sfn /tmp/cfgtest /tmp/srvup/letter-fun")
        b=await pg.evaluate("fetch('sync-config.js').then(r=>r.text())")
        ok1=a and "changed" in b
        await ctx.set_offline(True); c=await pg.evaluate("fetch('sync-config.js').then(r=>r.text()).catch(e=>'ERR')"); await ctx.set_offline(False)
        ok2="changed" in c   # offline falls back to the last good copy
        print("  ok  " if ok1 else "  FAIL", "sync-config.js is network-first: a changed config is served on the very next request")
        print("  ok  " if ok2 else "  FAIL", "offline: the last good copy of sync-config.js is served")
        await br.close()
        os.system("ln -sfn /workspace/letter-fun /tmp/srvup/letter-fun")
        print("FAILS:",int(not ok1)+int(not ok2))
asyncio.run(main())
