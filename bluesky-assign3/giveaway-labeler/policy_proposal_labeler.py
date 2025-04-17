import pandas as pd 
import re
import time 
import json 
from atproto import Client
from dotenv import load_dotenv
import os 
#from atproto.xrpc_client.models import XrpcError

load_dotenv(override=True)
USERNAME = os.getenv("USERNAME")
PW = os.getenv("PW")

client = Client()
client.login(USERNAME, PW)

df_keywords = pd.read_csv("bluesky-assign3/giveaway-labeler/giveaway-words.csv")
giveaway_words = df_keywords['Words'].dropna().tolist()
cta_words = df_keywords['call-to-action'].dropna().tolist()

df_urls = pd.read_csv("bluesky-assign3/bluesky_giveaway_labels.csv")
post_urls = df_urls['URL'].dropna().tolist()

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

        text = post["value"]["text"]

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

    #except XrpcError as e:
      #  print(f"XrpcError processing URL {url}: {e.message}")
      #  continue

    except Exception as e:
        print(f"Skipping URL (missing or invalid post): {url}")
        continue

print(f"Confirmed {len(confirmed_matches)} posts with BOTH a giveaway word and a CTA.")