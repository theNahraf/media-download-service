"""
One-time setup script to generate a Google Drive OAuth2 refresh token.

Run this ONCE on your local machine:
    python3 setup_gdrive_oauth.py

It will:
1. Open a browser for you to login with your Google account (the one with 5TB)
2. Generate a token.json file with a refresh token
3. Copy the refresh token to your .env file

After running this, you never need to run it again — the refresh token persists.
"""
import os
import json

# Must install these: pip3 install google-auth-oauthlib google-api-python-client
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDENTIALS_DIR = os.path.join(os.path.dirname(__file__), "credentials")
CLIENT_SECRET_FILE = os.path.join(CREDENTIALS_DIR, "gdrive-client-secret.json")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "gdrive-token.json")


def main():
    print("=" * 60)
    print("  Google Drive OAuth2 Setup")
    print("=" * 60)
    print()

    if not os.path.exists(CLIENT_SECRET_FILE):
        print("❌ Client secret file not found!")
        print(f"   Expected at: {CLIENT_SECRET_FILE}")
        print()
        print("To create it:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
        print("3. Application type: 'Desktop app'")
        print("4. Download the JSON and save it as:")
        print(f"   {CLIENT_SECRET_FILE}")
        return

    print("🔐 Opening browser for Google authorization...")
    print("   Sign in with your Google account that has the 5TB storage.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the token
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print()
    print("✅ Token saved to:", TOKEN_FILE)
    print()
    print("📋 Add these to your .env file:")
    print(f"   GDRIVE_CLIENT_ID={creds.client_id}")
    print(f"   GDRIVE_CLIENT_SECRET={creds.client_secret}")
    print(f"   GDRIVE_REFRESH_TOKEN={creds.refresh_token}")
    print()
    print("🎉 Setup complete! Your server will now upload files as YOUR account.")


if __name__ == "__main__":
    main()
