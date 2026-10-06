"""Render + upload the oldest APPROVED, unpublished item in queue/."""
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from common import all_items, load_item, save_item
from render import render


def upload(video, item):
    creds = Credentials(
        None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": item["title"][:100],
                    "description": item["description"] + "\n\n#shorts #motivation #story",
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
            item["youtube_id"] = upload(video, item)
            item["published"] = True
            save_item(path, item)
            print("Uploaded:", item["youtube_id"])
            return
    print("Nothing approved in queue/. Review a draft and set \"approved\": true.")


if __name__ == "__main__":
    main()
