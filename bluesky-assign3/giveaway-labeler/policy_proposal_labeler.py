import pandas as pd 
import re
import time 
import json 
from atproto import Client
from dotenv import load_dotenv
import os 
import requests
#from atproto.xrpc_client.models import XrpcError

load_dotenv(override=True)
USERNAME = os.getenv("USERNAME")
PW = os.getenv("PW")
API_KEY = os.getenv("SAFE_BROWSING_API_KEY")
SAFE_BROWSING_URL = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={API_KEY}"

client = Client()
client.login(USERNAME, PW)

df_keywords = pd.read_csv("bluesky-assign3/giveaway-labeler/giveaway-words.csv")
giveaway_words = df_keywords['Words'].dropna().tolist()
cta_words = df_keywords['call-to-action'].dropna().tolist()

df_urls = pd.read_csv("bluesky-assign3/bluesky_giveaway_labels.csv")
post_urls = df_urls['URL'].dropna().tolist()


def check_urls_with_safe_browsing(urls):
    body = {
        "client": {
            "clientId": "your-client-id",  # Just a unique name
            "clientVersion": "1.0"
        },
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url} for url in urls]
        }
    }

    response = requests.post(SAFE_BROWSING_URL, json=body)
    response.raise_for_status()
    matches = response.json()

    if "matches" in matches:
        return False
    else:
        return True


confirmed_matches = []

for url in post_urls:
    try:
        parts = url.split('/post/')
        did = parts[0].split('/')[-1]
        rkey = parts[1]

        post = client.com.atproto.repo.get_record({
            "repo": did,
            "collection": "app.bsky.feed.post",
            "rkey": rkey
        })

        post_value = post["value"]
        embed = post_value["embed"]
        text = post_value["text"]

        has_giveaway = any(re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) for word in giveaway_words)
        has_cta = any(re.search(rf"\b{re.escape(cta)}\b", text, re.IGNORECASE) for cta in cta_words)

        if has_giveaway and has_cta:
            actor_info = client.app.bsky.actor.get_profile({'actor':did})
            actor_info_dict = actor_info.dict()
            confirmed_matches.append({
                "url": url,
                "did": did,
                "rkey": rkey,
                "text": text,
                "followers_count": actor_info_dict.get("followersCount", 0),
                "follows_count": actor_info_dict.get("followsCount", 0),
                "posts_count": actor_info_dict.get("postsCount", 0),
                "created_at": actor_info_dict.get("createdAt", "")

            })

            time.sleep(1)
        
        # Check Google safe browsing API
        # Use set to prevent duplicates
        external_urls = set()

        # Regex check for URLs
        found_urls = re.findall(r'https?://\S+', text)
        external_urls.update(found_urls) # update from list to set

        # Check for URLs in facets
        facets = post_value["facets"]
        if facets:
            for f in facets:
                for feature in f["features"]:
                    feature_dict = feature.__dict__
                    if "uri" in feature_dict:
                        external_urls.add(feature_dict["uri"])
        
        # Check for URLs in embed
        if embed:
            embed_dict = embed.__dict__
            external = embed_dict.get("external")
            if external:
                external_dict = external.__dict__
                if "uri" in external_dict:
                    external_urls.add(external_dict["uri"])
        if external_urls:
            safe = check_urls_with_safe_browsing(list(external_urls))
            if not safe:
                print("Found unsafe URL in post:", post)

    #except XrpcError as e:
      #  print(f"XrpcError processing URL {url}: {e.message}")
      #  continue

    except Exception as e:
        print(f"Skipping URL (missing or invalid post): {url}")
        continue

print(f"Confirmed {len(confirmed_matches)} posts with BOTH a giveaway word and a CTA.")