#!/usr/bin/env bash
# v25 Family sync: one-time backend setup (Firebase Realtime Database + anonymous Auth, free Spark plan, no card).
# Needs ONE human step: run this in a Terminal on the box desktop and sign in with Google in the browser it opens.
#   bash /workspace/letter-fun/tools/sync/setup.sh            # set up + write beta/sync-config.js
#   bash /workspace/letter-fun/tools/sync/setup.sh --live     # ... and the live root sync-config.js too
# Re-running is safe (it reuses the project / family id saved in /workspace/secrets/letter-fun-sync.env).
# Prints no secrets. The web apiKey is a public identifier; access is enforced by database.rules.json.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
FB="npx --yes firebase-tools@15"
SEC=/workspace/secrets/letter-fun-sync.env; mkdir -p /workspace/secrets; chmod 700 /workspace/secrets; touch "$SEC"; chmod 600 "$SEC"
get(){ { grep -s "^$1=" "$SEC" || true; } | tail -1 | cut -d= -f2-; }
put(){ grep -v "^$1=" "$SEC" > "$SEC.tmp" || true; echo "$1=$2" >> "$SEC.tmp"; mv "$SEC.tmp" "$SEC"; chmod 600 "$SEC"; }
cd "$HERE"
if ! $FB login:list 2>/dev/null | grep -qi "logged in as"; then
  echo ">>> Not logged in: run  npx --yes firebase-tools@15 login --no-localhost  , open the URL on your own device, then feed_code.sh"; exit 1
fi
PROJECT=${PROJECT:-$(get PROJECT)}; [ -n "$PROJECT" ] || PROJECT="letter-fun-$(openssl rand -hex 3)"; put PROJECT "$PROJECT"
if ! $FB projects:list --json 2>/dev/null | grep -q "\"$PROJECT\""; then
  echo ">>> creating Firebase project $PROJECT"
  $FB projects:create "$PROJECT" --display-name "Letter Fun" || { echo "!!! Project creation failed. If this Google account has never used Firebase, open https://console.firebase.google.com once on your own device (same Google account), accept the terms, then re-run this script."; exit 1; }
fi
INST="$PROJECT-default-rtdb"
if ! $FB database:instances:list --project "$PROJECT" 2>/dev/null | grep -q "$INST"; then
  $FB database:instances:create "$INST" --location us-central1 --project "$PROJECT"
fi
DB="https://$INST.firebaseio.com"; put DB "$DB"
FAM=$(get FAM); [ -n "$FAM" ] || { FAM="fam-$(openssl rand -hex 12)"; put FAM "$FAM"; }
# rules + anonymous sign-in (the deploy creates a "Default Web App" if there is none)
$FB deploy --only database,auth --project "$PROJECT" --non-interactive
APPID=$($FB apps:list WEB --project "$PROJECT" --json | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s).result||[];process.stdout.write((r[0]||{}).appId||"")})')
KEY=$($FB apps:sdkconfig WEB "$APPID" --project "$PROJECT" --json | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const m=/"apiKey"\s*:\s*\\?"([^"\\]+)/.exec(s);process.stdout.write(m?m[1]:"")})')
[ -n "$KEY" ] || { echo "!!! could not read the web app config"; exit 1; }
put APIKEY "$KEY"
write(){ cat > "$1" <<CFG
// v25: family cloud sync settings (written by tools/sync/setup.sh). The apiKey is Firebase's public web identifier, not a
// secret; reads/writes are allowed only for devices linked with the family sync password (see tools/sync/database.rules.json).
window.LF_SYNC_CONFIG={apiKey:"$KEY",db:"$DB",fam:"$FAM"};
CFG
echo "wrote $1"; }
write "$REPO/beta/sync-config.js"
[ "${1:-}" = "--live" ] && write "$REPO/sync-config.js"
# self-test on a throwaway family id against the real backend, then remove it
ST="selftest-$(date +%s)"; node "$HERE/selftest.js" "$KEY" "$DB" "$ST"; $FB database:remove "/lf/$ST" --project "$PROJECT" --force >/dev/null 2>&1 || true
echo ">>> done: Firebase project $PROJECT is ready. Tell Grok Bot \"family sync is set up\" (it tests, commits and pushes)."
