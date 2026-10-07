"""Render the oldest APPROVED, unpublished item in queue/. Upload to YouTube if credentials exist;
otherwise leave the finished MP4 + a title/description text file in out/ (the workflow attaches them
as a downloadable artifact so you can upload by hand)."""
import os
from common import ROOT, all_items, load_item, save_item
from render import render


def have_youtube():
    return all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def upload(video, item):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials(
        None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": item["title"][:100],
                    "description": item["description"] + "\n\n#shorts #story #motivation",
                    "tags": item.get("tags", []), "categoryId": "22"},
        "status": {"privacyStatus": os.environ.get("PRIVACY", "private"),  # start private!
                   "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def main():
    for path in all_items():
        item = load_item(path)
        if item.get("approved") and not item.get("published"):
            print("Publishing", path.name, "-", item["title"])
            video = render(item, path.stem)
            sidecar = ROOT / "out" / f"{path.stem}.txt"
            sidecar.write_text(
                f"TITLE:\n{item['title']}\n\nDESCRIPTION:\n{item['description']}\n\n#shorts #story #motivation\n\n"
                f"TAGS:\n{', '.join(item.get('tags', []))}\n", encoding="utf-8")
            if have_youtube():
                item["youtube_id"] = upload(video, item)
                print("Uploaded:", item["youtube_id"])
            else:
                item["manual_upload_needed"] = True
                print("No YouTube credentials - video saved to out/ (download it from the run's Artifacts).")
            item["published"] = True
            save_item(path, item)
            return
    print("Nothing approved in queue/. Review a draft and set \"approved\": true.")


if __name__ == "__main__":
    main()
