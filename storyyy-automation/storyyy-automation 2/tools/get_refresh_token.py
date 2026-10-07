"""Run ONCE on your own computer to get YT_REFRESH_TOKEN.
pip install google-auth-oauthlib ; put your OAuth 'Desktop app' file next to this as client_secret.json"""
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", ["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nYT_REFRESH_TOKEN =", creds.refresh_token)
