# Storyyy Timee - semi-automated Shorts pipeline (all free tiers)

Daily flow
1. 03:00 UTC  `generate.yml` asks Gemini for a new ORIGINAL story -> `queue/<timestamp>.json` (approved: false)
2. You open the file on github.com (works on a phone), tweak the wording, set `"approved": true`, commit.
3. 14:00 UTC  `publish.yml` renders the oldest approved item (voice + stock footage + captions) and uploads it.

The 30-second review in step 2 is deliberate: YouTube demonetizes fully automated, templated channels.
Your edits and your own angle are what keep the channel eligible.

## One-time setup
1. Create a GitHub repo (public = unlimited free Actions minutes), push these files.
2. Keys (all free):
   - GEMINI_API_KEY: https://aistudio.google.com/apikey
   - PEXELS_API_KEY: https://www.pexels.com/api/
3. YouTube upload credentials:
   - console.cloud.google.com -> new project -> enable "YouTube Data API v3"
   - OAuth consent screen -> add yourself as test user, then PUBLISH the app ("In production").
     If you leave it in "Testing", the refresh token expires after 7 days and uploads will break.
   - Credentials -> OAuth client ID -> Desktop app -> download as `client_secret.json`
   - Run `python tools/get_refresh_token.py` on your computer and sign in with the channel's account.
4. Repo -> Settings -> Secrets and variables -> Actions -> add secrets:
   GEMINI_API_KEY, PEXELS_API_KEY, YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
5. Uploads default to PRIVATE. When you trust the output, add a repo *variable* PRIVACY = public.
6. Run "Generate draft" manually (Actions tab -> Run workflow) to test, approve it, run "Publish approved video".

## Known limits / things to verify
- Unaudited API projects: YouTube may force API uploads to private until you pass the API compliance audit. Check this before relying on it.
- Upload quota is about 6 videos/day on the default free quota; this pipeline posts 1/day.
- Gemini model name (GEMINI_MODEL env) may need updating if Google retires it.
- Optional: put a royalty-free `assets/music.mp3` in assets/ for quiet background music.
- If you publish realistic-looking synthetic content, check YouTube's AI disclosure setting.
- Scheduled workflows can pause after long repo inactivity; re-enable in the Actions tab if so.
