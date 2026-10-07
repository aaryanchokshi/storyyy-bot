# Storyyy Timee Studio - story Shorts on autopilot (free tools only)

A GitHub-only pipeline: it writes a story, picks the strongest opening hook, lints the title,
renders a vertical video (free voice + free stock footage + captions) and - if you want - uploads it.
You stay in the loop for 30 seconds per video. That human step is what keeps the channel
eligible for monetization: YouTube demonetizes fully automated, templated channels.

## How a day works
1. 03:00 UTC  "Generate draft"
   - Gemini writes 7 candidate hooks, each from a different one of 21 hook formulas
   - hookscore.py scores them; the best becomes line 1 of the story
   - Gemini writes the story + 3 titles; title.py lints them; the best title wins
   - draft saved to queue/<time>.json with approved=false
2. YOU: open the draft on github.com (phone is fine). Look at "review" at the bottom:
   other hooks and titles with scores. Swap if you like (paste into lines[0].text or title).
   Fix any wording. Set "approved": true. Commit.
3. 14:00 UTC  "Publish approved video": renders it. Then either
   - uploads to YouTube (if you added the YouTube secrets), or
   - saves the MP4 + a title/description .txt as a downloadable file: open the run in the Actions tab,
     scroll to "Artifacts", download "video", upload in the YouTube app (2 minutes).

## The learning loop (what makes it get better)
When a video has some views: YouTube Studio -> Analytics -> that video -> Engagement ->
audience retention chart -> download icon -> "Audience retention". Rename the file like
`thunder-night_45s.csv` (the number = video length in seconds) and upload it into the `retention/`
folder on GitHub. A workflow writes a plain-English report into `reports/`
(hook leak, cliffs, slide) and the next drafts are written with those lessons in the prompt.

## Setup - pick ONE path
PATH A (easiest, 15 min): no YouTube API at all
  secrets: GEMINI_API_KEY and at least one of PIXABAY_API_KEY / PEXELS_API_KEY
PATH B (full auto-upload): Path A + YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
  1. console.cloud.google.com -> new project -> enable "YouTube Data API v3"
  2. OAuth consent screen -> add yourself as test user -> PUBLISH the app ("In production").
     (Left in "Testing", the token dies after 7 days.)
  3. Credentials -> OAuth client ID -> Desktop app -> download as client_secret.json
  4. On your computer: pip install google-auth-oauthlib ; python tools/get_refresh_token.py
  Uploads default to PRIVATE. Add a repo VARIABLE  PRIVACY = public  when you trust the output.

Keys: Gemini https://aistudio.google.com/apikey | Pixabay: sign up, key at https://pixabay.com/api/docs/
| Pexels https://www.pexels.com/api/ (new keys are sometimes unavailable)
Add them in: repo Settings -> Secrets and variables -> Actions.

First test: Actions tab -> "Generate draft" -> Run workflow. Approve the draft.
Then "Publish approved video" -> Run workflow.

## Make it yours
- config/channel.md  your narrator voice, rules and series ideas. Edit it - this is your edge.
- assets/music.mp3   optional royalty-free background track (mixed quietly).
- src/generate.py    THEMES and STRUCTURES lists.

## Honest limits
- hookscore is a rough heuristic (its author says it separates bad hooks from real ones, not a
  creator's hits from misses). Use it as a filter, trust your own ear.
- The 21 formulas were written for creator videos; the prompt adapts them to storytelling.
- Path B: YouTube may force API uploads to private until the API project passes an audit. Check early.
- Gemini model name (env GEMINI_MODEL) may need updating if Google retires it.
- Free API quotas change. Pixabay/Pexels clips are mostly landscape and get center-cropped.
- Scheduled workflows can pause after long repo inactivity; re-enable in the Actions tab.
- YouTube Partner Program thresholds apply before you earn anything - check YouTube's help page.

## Credits
vendor/youtube-agent-skill/ is "The YouTube agent skill" by Jake Schincariol, MIT licence
(https://github.com/Jakeschincariol/youtube-agent-skill). Its hook formulas and scoring/lint/retention
tools are used here unmodified. The other 8 skills in that folder are prompts you can paste into a Claude chat.
