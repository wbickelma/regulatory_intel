# -*- coding: utf-8 -*-
"""Inoreader + RSS.app Full Workflow Script"""

import requests
import json
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# https://www.inoreader.com/oauth2/auth/?client_id=1000013775&redirect_uri=http://localhost&response_type=code&scope=read%20write&state=774411

# --- CONFIGURATION ---
# Fixed the typo in CLIENT_ID_INOREADER
CLIENT_ID = os.getenv("CLIENT_ID_INOREADER") 
CLIENT_SECRET = os.getenv("CLIENT_SECRET_INOREADER")
REDIRECT_URI = "http://localhost"
TOKEN_FILE = "inoreader_tokens.json"

rss_app_key = os.getenv("RSS_APP_KEY")
rss_app_secret = os.getenv("RSS_APP_SECRET")

# 🚨 IMPORTANT: If you want to use a new AUTH_CODE, you MUST delete the 
# existing 'inoreader_tokens.json' file from your directory first!
AUTH_CODE = "1e5953b01dde5b2f26995324a8c6e409d6100fe0" 


# ==========================================
#      INOREADER AUTHENTICATION LOGIC
# ==========================================

def get_initial_tokens(auth_code):
    print("Fetching initial tokens...")
    url = "https://www.inoreader.com/oauth2/token"
    data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        save_tokens(tokens)
        print("✅ Successfully generated and saved initial tokens.")
        return tokens
    else:
        print(f"❌ Error getting initial tokens: {response.text}")
        return None

def refresh_access_token(refresh_token):
    print("🔄 Access token expired. Refreshing token...")
    url = "https://www.inoreader.com/oauth2/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        new_tokens = response.json()
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token
        save_tokens(new_tokens)
        print("✅ Successfully refreshed tokens.")
        return new_tokens
    else:
        print(f"❌ Failed to refresh token: {response.text}")
        return None

def save_tokens(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

def get_valid_access_token():
    tokens = load_tokens()
    if not tokens:
        if not AUTH_CODE:
            print("❌ No tokens found and no AUTH_CODE provided.")
            return None
        tokens = get_initial_tokens(AUTH_CODE)
    return tokens


# ==========================================
#          RSS.APP API LOGIC
# ==========================================

def create_rss_feed(source_url):
    print(f"\n--- Generating RSS feed for: {source_url} ---")
    endpoint = "https://api.rss.app/v1/feeds"
    headers = {
        "Authorization": f"Bearer {rss_app_key}:{rss_app_secret}",
        "Content-Type": "application/json"
    }
    payload = {"url": source_url}
    
    response = requests.post(endpoint, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        data = response.json()
        feed_url = data.get('rss_feed_url')
        print(f"✅ Feed successfully generated: {feed_url}")
        return feed_url
    else:
        print(f"❌ RSS.app Error {response.status_code}: {response.text}")
        return None


# ==========================================
#          INOREADER API LOGIC
# ==========================================

def add_feed_to_specific_folder(feed_url, folder_name, tokens):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # STEP 1: SUBSCRIBE
    print(f"\n--- 1. Subscribing to {feed_url} ---")
    add_url = "https://www.inoreader.com/reader/api/0/subscription/quickadd"
    add_data = {
        "quickadd": feed_url,
        "AppId": CLIENT_ID,
        "AppKey": CLIENT_SECRET
    }

    add_res = requests.post(add_url, headers=headers, data=add_data)
    
    # Catch expired token and refresh
    if add_res.status_code == 401:
        tokens = refresh_access_token(tokens['refresh_token'])
        if not tokens: return None
        headers["Authorization"] = f"Bearer {tokens['access_token']}"
        add_res = requests.post(add_url, headers=headers, data=add_data)

    if add_res.status_code != 200:
        print(f"❌ Failed to subscribe: {add_res.text}")
        return None

    try:
        feed_id = add_res.json().get('streamId')
        print(f"✅ Subscribed! Feed ID: {feed_id}")
    except requests.exceptions.JSONDecodeError:
        print("❌ Could not parse Feed ID")
        return None

    # STEP 2: ASSIGN TO FOLDER
    print(f"\n--- 2. Moving feed to folder: '{folder_name}' ---")
    edit_url = "https://www.inoreader.com/reader/api/0/subscription/edit"
    folder_tag = f"user/-/label/{folder_name}"

    edit_data = {
        "ac": "edit",
        "s": feed_id,
        "a": folder_tag,
        "AppId": CLIENT_ID,
        "AppKey": CLIENT_SECRET
    }

    tag_res = requests.post(edit_url, headers=headers, data=edit_data)

    if tag_res.status_code == 200:
        print(f"🚀 Successfully added feed to '{folder_name}'!")
        return tokens # Returning tokens in case they were refreshed
    else:
        print(f"❌ Failed to move to folder: {tag_res.text}")
        return tokens


def get_folder_articles(folder_name, tokens, days_back=7):
    print(f"\n--- 3. Fetching articles from '{folder_name}' (Last {days_back} days) ---")
    stream_id = f"user/-/label/{folder_name}"
    cutoff_time = int(time.time()) - (days_back * 24 * 60 * 60)
    url = f"https://www.inoreader.com/reader/api/0/stream/contents/{stream_id}"

    params = {
        "AppId": CLIENT_ID,
        "AppKey": CLIENT_SECRET,
        "n": 50,
        "ot": cutoff_time 
    }
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = requests.get(url, headers=headers, params=params)

    # Catch expired token and refresh
    if response.status_code == 401:
        tokens = refresh_access_token(tokens['refresh_token'])
        if not tokens: return
        headers["Authorization"] = f"Bearer {tokens['access_token']}"
        response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        items = response.json().get('items', [])
        print(f"✅ Found {len(items)} articles.\n")
        for item in items:
            title = item.get('title', 'No Title')
            published_ts = item.get('published', 0)
            pub_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(published_ts))
            link = item.get('canonical', [{}])[0].get('href', 'No Link')
            print(f"📰 {title}\n🕒 {pub_date}\n🔗 {link}\n")
    else:
        print(f"❌ Error fetching folder contents: {response.text}")


# ==========================================
#              EXECUTION BLOCK
# ==========================================

if __name__ == "__main__":
    
    # 1. Verify environment variables loaded
    if not CLIENT_ID or not rss_app_key:
        print("⚠️ Missing credentials. Check your .env file!")
        exit()

    # 2. Get or load Inoreader Tokens
    current_tokens = get_valid_access_token()

    if current_tokens:
        
        # 3. Generate RSS Feed from Target URL
        target_website = "https://www.skadden.com/insights?skip=0&panelid=tab-find-mode&paneltogglestate=2&type=9cbfe518-3bc0-4632-ae13-6ac9cee8eb31&hassearched=true"
        generated_rss_url = create_rss_feed(target_website)
        
        if generated_rss_url:
            target_folder = 'test_folder2'
            
            # 4. Add to Inoreader Folder (Catches potentially refreshed tokens)
            current_tokens = add_feed_to_specific_folder(generated_rss_url, target_folder, current_tokens)
            
            # 5. Fetch Articles
            if current_tokens:
                get_folder_articles(target_folder, current_tokens, days_back=7)