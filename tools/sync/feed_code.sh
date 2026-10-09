#!/usr/bin/env bash
# Finishes the no-browser Firebase login with the authorization code, then runs setup.sh --live.
# The code comes from (first found): stdin (when piped), $FIREBASE_AUTH_CODE, or /workspace/secrets/fb_code.txt (deleted after use).
#   echo "<code>" | bash /workspace/letter-fun/tools/sync/feed_code.sh
# Prints only the account email and progress. Never prints the code or any token.
# (The CLI keeps the pending login's one-time verifier in ~/.config/configstore, so the URL stays valid until
#  `firebase login --no-localhost` is run again; no process has to stay running.)
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); SEC=/workspace/secrets; FB="npx --yes firebase-tools@15"
CODE=""; FROMFILE=0
if [ ! -t 0 ]; then CODE=$(head -c 4096 | tr -d '[:space:]'); fi
[ -n "$CODE" ] || CODE=$(printf '%s' "${FIREBASE_AUTH_CODE:-}" | tr -d '[:space:]')
if [ -z "$CODE" ] && [ -s "$SEC/fb_code.txt" ]; then CODE=$(tr -d '[:space:]' < "$SEC/fb_code.txt"); FROMFILE=1; fi
unset FIREBASE_AUTH_CODE
[ -n "$CODE" ] || { echo "!!! no code given (pipe it in, set FIREBASE_AUTH_CODE, or put it in $SEC/fb_code.txt)"; exit 2; }
email(){ $FB login:list 2>/dev/null | grep -i "logged in as" | head -1 | sed -E 's/.*[Ll]ogged in as[[:space:]]+//; s/[[:space:]]*$//'; }
E=$(email)
if [ -z "$E" ]; then
  node -e 'try{const j=require(process.env.HOME+"/.config/configstore/firebase-tools.json"); process.exit(j.tempLoginState&&j.tempLoginState.codeVerifier?0:1)}catch(e){process.exit(1)}' \
    || { echo "!!! no pending login on this box (the one-time session is gone). Ask for a fresh URL: cd $HERE && npx --yes firebase-tools@15 login --no-localhost"; exit 3; }
  echo ">>> completing the login ..."
  OUT=$($FB login --no-localhost "$CODE" 2>&1); RC=$?
  # show the CLI's answer without ever echoing the code
  printf '%s\n' "$OUT" | sed -E "s/$CODE/[code]/g" | sed -E 's/(ya29|1\/\/)[A-Za-z0-9._-]+/[token]/g' | tail -6
  [ "$FROMFILE" = 1 ] && rm -f "$SEC/fb_code.txt"
  for i in 1 2 3 4 5 6; do E=$(email); [ -n "$E" ] && break; sleep 2; done
  [ -n "$E" ] || { echo "!!! login did not complete (wrong or expired code?). The URL is still valid for a fresh code unless it was already used; otherwise request a new URL."; exit 4; }
else
  [ "$FROMFILE" = 1 ] && rm -f "$SEC/fb_code.txt"
fi
unset CODE OUT
echo "Logged in as $E"
echo ">>> running setup.sh --live (project, database, rules, anonymous sign-in, self-test) ..."
bash "$HERE/setup.sh" --live
RC=$?
[ $RC -eq 0 ] && echo ">>> setup finished OK for $E" || echo "!!! setup.sh exited with code $RC (see output above; it is safe to re-run feed_code.sh with any code, or setup.sh directly: it skips login now)"
exit $RC
