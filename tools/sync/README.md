# Letter Fun · Family sync (v25)

Backend: Firebase Realtime Database (REST) + Firebase anonymous Auth, free Spark plan, no card. No server of our own.

* `setup.sh` – one-time setup after a Google sign-in on the box (creates the project, database, rules, anonymous
  sign-in; writes `sync-config.js`). Settings/ids are kept in `/workspace/secrets/letter-fun-sync.env` (600).
* `database.rules.json` – access control:
  * `lf/<fam>/has` – public `true` once a family sync password exists (the app uses it to show "create" vs "type").
  * `lf/<fam>/ph` – SHA-256 of the family sync password, written once, never readable.
  * `lf/<fam>/members/<uid>` – a device (anonymous uid) becomes a member by writing the matching hash.
  * `lf/<fam>/dev/<uid>` – each device's own record, writable only by that device, readable only by members.
* `selftest.js` – rules self-test (`node selftest.js` against the emulators; setup.sh runs it against the real backend).
* `firebase.json` – rules, anonymous auth provider, emulator ports (auth 9099, database 9000).

Device record (`dev/<uid>`): `{v:1,label,seen,app,players:{<player u>:{n,c,s,d,perm,b,br,t:{total,days,games,last},p:{items},pr}}}`
– each device's OWN counters only; merged on read by name (high scores max, time + right/wrong sums, newest delete vs
newest activity, time-stamped resets).
