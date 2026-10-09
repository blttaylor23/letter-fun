// v25: family cloud sync settings. null = sync is OFF (the app works exactly as before, nothing leaves the device).
// Filled in by tools/sync/setup.sh after the one-time Firebase sign-in: {apiKey, db, fam}. The apiKey is a public
// Firebase web key (not a secret); access is controlled by database.rules.json + the family sync password.
window.LF_SYNC_CONFIG=null;
