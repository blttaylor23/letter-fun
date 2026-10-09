// Rules self-test with sync.js itself. node selftest.js                -> local emulators (tests)
//                                     node selftest.js KEY DB FAM    -> the real backend (setup.sh), throwaway family id
const fs=require("fs"), vm=require("vm"), path=require("path");
const REAL=process.argv[2]?{apiKey:process.argv[2],db:process.argv[3],fam:process.argv[4]}:null;
const EMU={apiKey:"demo-key",db:"http://127.0.0.1:9000",dbq:"ns=demo-letterfun-default-rtdb",fam:"famtest"+process.pid,authBase:"http://127.0.0.1:9099/identitytoolkit.googleapis.com",tokenBase:"http://127.0.0.1:9099/securetoken.googleapis.com"};
const C=REAL||EMU;
function client(){ const store={}; const ctx={window:{LF_SYNC_CONFIG:C},
  localStorage:{getItem:k=>k in store?store[k]:null,setItem:(k,v)=>{store[k]=String(v)},removeItem:k=>{delete store[k]}},fetch,AbortController,TextEncoder,crypto:globalThis.crypto,setTimeout,clearTimeout,console};
  vm.createContext(ctx); vm.runInContext(fs.readFileSync(path.join(__dirname,"../../beta/sync.js"),"utf8"),ctx); return ctx.window.LFSync; }
let fails=0; const ok=(c,m)=>{ console.log((c?"  ok   ":"  FAIL ")+m); if(!c) fails++; };
const raw=async(m,p,b,tok)=>{ const r=await fetch(C.db+"/lf/"+C.fam+"/"+p+".json?"+(C.dbq||"")+(tok?"&auth="+tok:""),{method:m,body:b===undefined?undefined:JSON.stringify(b)}); return r.status; };
(async()=>{
  const A=client(), B=client(), X=client();
  ok(await A.hasPassword()===false, "no family password yet");
  let e=null; try{ await A.getAll(); }catch(x){ e=x; } ok(e&&e.denied, "unlinked device can't read");
  e=null; try{ await A.putDevice({v:1,players:{a:{n:"x"}}}); }catch(x){ e=x; } ok(e&&e.denied, "unlinked device can't write");
  e=null; try{ await A.link("abc",true); }catch(x){ e=x; } ok(e&&e.short, "password must be 6+ characters");
  ok(await A.link("tiger-moon-42",true), "A creates the family password and is linked");
  ok(await A.hasPassword()===true, "has=true is public");
  e=null; try{ await X.link("hacker-pass",true); }catch(x){ e=x; } ok(e&&e.exists, "nobody can replace the password");
  e=null; try{ await X.link("wrong-pass",false); }catch(x){ e=x; } ok(e&&e.wrong, "wrong password is refused");
  ok(await B.link("tiger-moon-42",false), "B links with the right password");
  await A.putDevice({v:1,label:"A",players:{u1:{n:"Blakeli"}}}); await B.putDevice({v:1,label:"B",players:{u2:{n:"Blakeli"}}});
  const all=await B.getAll(); ok(Object.keys(all).length===2, "linked devices read every device record");
  const ta=(await A.token()), tb=await B.token();
  ok(await raw("PUT","dev/"+ta.uid,{v:1,players:{z:{n:"evil"}}},tb.id)===401, "B can't overwrite A's record");
  ok(await raw("PUT","dev/"+tb.uid,{v:2,players:{}},tb.id)===401, "malformed record refused");
  ok(await raw("GET","ph",undefined,tb.id)===401, "the password hash is never readable");
  ok(await raw("GET","members",undefined,tb.id)===401, "the member list is not readable");
  ok(await raw("GET","",undefined,null)===401 && await raw("GET","dev",undefined,(await X.token()).id)===401, "not listable without being linked");
  ok(await X.checkLinked()===false && await B.checkLinked()===true, "checkLinked");
  await B.unlink(); e=null; try{ await B.getAll(); }catch(x){ e=x; } ok(e&&e.denied && !B.status().linked, "unlinked again: no access");
  console.log("\nFAILS:",fails); process.exit(fails?1:0);
})().catch(e=>{ console.log("CRASH",e); process.exit(2); });
